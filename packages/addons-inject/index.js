/* Module to inject the new Addons implementation on pages served by El Proxito.
 *
 * This module is run as a Cloudflare Worker and modifies files with two different purposes:
 *
 *   1. remove the old implementation of our flyout (``readthedocs-doc-embed.js`` and others)
 *   2. inject the new Addons implementation (``readthedocs-addons.js``) script
 *
 * Currently, we are performing both of these operations for all projects, except
 * those that have opted out of Addons.
 */

/** Class to wrap all module constants, reused in tests
 *
 * This is a slightly silly hack because Workers can't export strings, though
 * exported classes seem to be fine. These should really be strings in a
 * separate import, but this complicates the Worker deployment a little.
 **/
export class AddonsConstants {
  // Add "readthedocs-addons.js" inside the "<head>"
  static scriptAddons =
    '<script async type="text/javascript" src="/_/static/javascript/readthedocs-addons.js"></script>';

  // Selectors we want to remove
  // https://developers.cloudflare.com/workers/runtime-apis/html-rewriter/#selectors
  static removalScripts = [
    'script[src="/_/static/javascript/readthedocs-analytics.js"]',
    'script[src="/_/static/javascript/readthedocs-doc-embed.js"]',
    'script[src="/_/static/core/js/readthedocs-doc-embed.js"]',
    'script[src="https://assets.readthedocs.org/static/javascript/readthedocs-analytics.js"]',
    'script[src="https://assets.readthedocs.org/static/javascript/readthedocs-doc-embed.js"]',
    'script[src="https://assets.readthedocs.org/static/core/js/readthedocs-doc-embed.js"]',
  ];
  static removalLinks = [
    'link[href="/_/static/css/readthedocs-doc-embed.css"]',
    'link[href="https://assets.readthedocs.org/static/css/readthedocs-doc-embed.css"]',
    // Badge only and proxied stylesheets
    'link[href="https://assets.readthedocs.org/static/css/badge_only.css"]',
    'link[href="/_/static/css/badge_only.css"]',
  ];
  static removalElements = [
    // Sphinx-rtd-theme version warning
    "[role=main] > div:first-child > div:first-child.admonition.warning",
    // Furo version warning
    "[role=main] > div:first-child.admonition.warning",
    // Book version warning
    "#main-content > div > div > article > div:first-child.admonition.warning",
    // Flyout
    "div.rst-versions",
  ];

  // Additional replacements that we perform
  static replacements = {
    searchtools: {
      pattern: `/* Search initialization removed for Read the Docs */`,
      replacement: `
/* Search initialization manipulated by Read the Docs using Cloudflare Workers */
/* See https://github.com/readthedocs/addons/issues/219 for more information */

function initializeSearch() {
  Search.init();
}

if (document.readyState !== "loading") {
  initializeSearch();
}
else {
  document.addEventListener("DOMContentLoaded", initializeSearch);
}`,
    },
  };
}

// "readthedocsDataParse" is the "<script>" that calls:
//
//   READTHEDOCS_DATA = JSON.parse(document.getElementById('READTHEDOCS_DATA').innerHTML);
//
const readthedocsDataParse = "script[id=READTHEDOCS_DATA]:first-of-type";
const readthedocsData = "script[id=READTHEDOCS_DATA]";

async function onFetch(request, env, context) {
  // Avoid blank pages on exceptions
  context.passThroughOnException();

  const response = await fetch(request);

  if (response.body === null) {
    // TODO This was encountered when Cloudflare already has a request cached
    // and could respond with a 304 response. It's not clear if this is
    // necessary or wanted yet.
    console.debug("Response body was already null, passing through.");
    return response;
  }

  try {
    const transformed = await transformResponse(response);
    // Wait on the transformed body for errors to evaluate. Timeout errors and
    // errors thrown during transform aren't actually raised until the body is
    // read. If there was no return, we should return the original response.
    if (transformed !== undefined) {
      return new Response(await transformed.arrayBuffer(), transformed);
    }
  } catch (error) {
    console.error("Discarding error:", error);
    console.debug("Returning original response to avoid blank page");
  }

  return response;
}

export default {
  fetch: onFetch,
};

/** Transform HTTP reponses
 *
 * This supports several versions of element removal and transformation of some
 * content that was previously injected into project builds.
 *
 * Important: wait until the last minute to use a `response.clone()`, as if you
 * create a clone and do not use the body, this consumes extra memory in the
 * worker. Response cloning is required because `transform()` evaluates the
 * response body, which closes the read stream from any future reading. So, to
 * allow the original response to return when `transform()` fails, we clone the
 * response as we are calling transform and we know the cloned response body
 * will be evaluated.
 *
 * @param response {Response} - The origin response
 * @returns {Response} - If transformed, return a response, otherwise `null`.
 **/
async function transformResponse(response) {
  const { headers } = response;

  // Get the content type of the response to manipulate the content only if it's HTML
  const contentType = headers.get("content-type") || "";
  const injectHostingIntegrations =
    headers.get("x-rtd-hosting-integrations") || "false";
  const forceAddons = headers.get("x-rtd-force-addons") || "false";
  const httpStatus = response.status;

  // Log some debugging data
  console.log(`ContentType: ${contentType}`);
  console.log(`X-RTD-Force-Addons: ${forceAddons}`);
  console.log(`X-RTD-Hosting-Integrations: ${injectHostingIntegrations}`);
  console.log(`HTTP status: ${httpStatus}`);

  // Debug mode for some test cases. This is just for triggering an exception
  // from tests. There might be a way to conditionally enable this, but I had
  // trouble getting Wrangler vars to work at all.
  const throwError = headers.get("X-RTD-Debug-Throw-Error");
  if (throwError) {
    console.log(`Throw error: ${throwError}`);
  }

  // Get project/version slug from headers inject by El Proxito
  const projectSlug = headers.get("X-RTD-Project") || "";
  const versionSlug = headers.get("X-RTD-Version") || "";
  const resolverFilename = headers.get("X-RTD-Resolver-Filename") || "";
  const loadWhenEmbedded = headers.get("x-rtd-load-addons-when-embedded") || "false";

  // Check to decide whether or not inject Addons library. We only do this for
  // `text/html` content types.
  if (contentType.includes("text/html")) {
    // Remove old implementation of our flyout and inject the new addons if the following conditions are met:
    //
    // - header `X-RTD-Force-Addons` is present (user opted-in into new beta addons)
    // - header `X-RTD-Hosting-Integrations` is not present (added automatically when using `build.commands`)
    //
    if (forceAddons === "true" && injectHostingIntegrations === "false") {
      let rewriter = new HTMLRewriter();

      // Remove by selector lookup
      for (const script of AddonsConstants.removalScripts) {
        rewriter.on(script, new removeElement());
      }
      for (const link of AddonsConstants.removalLinks) {
        rewriter.on(link, new removeElement());
      }
      for (const element of AddonsConstants.removalElements) {
        rewriter.on(element, new removeElement());
      }

      // TODO match the pattern above and make this work
      // NOTE: I wasn't able to reliably remove the "<script>" that parses
      // the "READTHEDOCS_DATA" defined previously, so we are keeping it for now.
      //
      // rewriter.on(readthedocsDataParse, new removeElement())
      // rewriter.on(readthedocsData, new removeElement())

      rewriter
        .on("head", new addPreloads())
        .on(
          "head",
          new addMetaTags(
            projectSlug,
            versionSlug,
            resolverFilename,
            httpStatus,
            loadWhenEmbedded,
          ),
        );

      // This is only used for testing purposes. This is used to mimic an error
      // being thrown during the request to origin. There are cases that are
      // difficult to model here, like a large data URL timing out the request.
      if (throwError) {
        rewriter.on("*", {
          element(element) {
            throw new Error("Manually triggered error in transform");
          },
        });
      }

      return rewriter.transform(
        // Cloning is required. See function docs above.
        await response.clone(),
      );
    }
  }

  // Inject Addons if the following conditions are met:
  //
  // - header `X-RTD-Hosting-Integrations` is present (added automatically when using `build.commands`)
  // - header `X-RTD-Force-Addons` is not present (user opted-in into new beta addons)
  //
  if (forceAddons === "false" && injectHostingIntegrations === "true") {
    return new HTMLRewriter()
      .on("head", new addPreloads())
      .on(
        "head",
        new addMetaTags(projectSlug, versionSlug, resolverFilename, httpStatus, loadWhenEmbedded),
      )
      .transform(
        // Cloning is required. See function docs above.
        await response.clone(),
      );
  }

  // Modify `_static/searchtools.js` to re-enable Sphinx's default search
  if (
    (contentType.includes("text/javascript") ||
      contentType.includes("application/javascript")) &&
    (injectHostingIntegrations === "true" || forceAddons === "true") &&
    response.url.endsWith("_static/searchtools.js")
  ) {
    console.debug("Modifying _static/searchtools.js");
    // Note, not a `clone()` call here on purpose, as we create a new Response
    // in the function already.
    return handleSearchToolsJSRequest(response);
  }

  // Return null response, don't continue transforming this response
  return;
}

class removeElement {
  element(element) {
    console.log("Removing: " + element.tagName);
    console.log("Attribute href: " + element.getAttribute("href"));
    console.log("Attribute src: " + element.getAttribute("src"));
    console.log("Attribute id: " + element.getAttribute("id"));
    console.log("Attribute class: " + element.getAttribute("class"));
    element.remove();
  }
}

class addPreloads {
  element(element) {
    console.log("addPreloads");
    element.append(AddonsConstants.scriptAddons, { html: true });
  }
}

class addMetaTags {
  constructor(projectSlug, versionSlug, resolverFilename, httpStatus, loadWhenEmbedded) {
    this.projectSlug = projectSlug;
    this.versionSlug = versionSlug;
    this.resolverFilename = resolverFilename;
    this.httpStatus = httpStatus;
    this.loadWhenEmbedded = loadWhenEmbedded;
  }

  element(element) {
    console.log(
      `addProjectVersionSlug. projectSlug=${this.projectSlug} versionSlug=${this.versionSlug} resolverFilename=${this.resolverFilename}`,
    );
    if (this.projectSlug && this.versionSlug) {
      const metaProject = `<meta name="readthedocs-project-slug" content="${this.projectSlug}" />`;
      const metaVersion = `<meta name="readthedocs-version-slug" content="${this.versionSlug}" />`;
      const metaResolverFilename = `<meta name="readthedocs-resolver-filename" content="${this.resolverFilename}" />`;
      const metaHttpStatus = `<meta name="readthedocs-http-status" content="${this.httpStatus}" />`;
      const metaLoadWhenEmbedded = `<meta name="readthedocs-load-addons-when-embedded content="${this.loadWhenEmbedded}" />`;

      element.append(metaProject, { html: true });
      element.append(metaVersion, { html: true });
      element.append(metaResolverFilename, { html: true });
      element.append(metaHttpStatus, { html: true });
      element.append(metaLoadWhenEmbedded, { html: true });
    }
  }
}

/** Fix the old removal of the Sphinx search init.
 *
 * Enabling addons breaks the default Sphinx search in old versions that can't
 * be rebuilt. We previously patches the Sphinx search in the
 * `readthedocs-sphinx-ext` extension, but since old versions can't be rebuilt,
 * the fix does not apply there.
 *
 * To solve the problem in old versions, we are using a Cloudflare worker to
 * apply this fix at serving time for those old versions.
 *
 * The fix replaces a Read the Docs comment in file `_static/searchtools.js`
 * that disabled the initialization of Sphinx search_. This change was
 * originally introduced by `readthedocs-sphinx-ext` and commented out the
 * initialization of the default Sphinx search. This reverts manipulation and
 * restores the original Sphinx search initialization.
 *
 * @param response {Response} - Response from origin
 * @returns {Response}
 **/
async function handleSearchToolsJSRequest(response) {
  const { pattern, replacement } = AddonsConstants.replacements.searchtools;
  const content = await response.text();
  return new Response(content.replace(pattern, replacement), response);
}
