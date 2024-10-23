import { fetchMock, SELF } from "cloudflare:test";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import { AddonsConstants } from "../index";

beforeAll(() => {
  // Enable outbound request mocking...
  fetchMock.activate();
  // ...and throw errors if an outbound request isn't mocked
  fetchMock.disableNetConnect();
});

// Ensure we matched every mock we defined
afterEach(() => fetchMock.assertNoPendingInterceptors());

describe("Addons when disabled", async () => {
  it("skips injection on HTML based on headers", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/" })
      .reply(200, "<html></html>", {
        headers: {
          "Content-type": "text/html",
          "X-RTD-Force-Addons": false,
          "X-RTD-Hosting-Integrations": false,
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/",
    );
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("<html></html>");
  });
});

describe("Addons when enabled", async () => {
  it("handles HTML injection and no rewrites", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/" })
      .reply(200, "<html><head></head><body></body></html>", {
        headers: {
          "Content-type": "text/html",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": false,
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/",
    );
    expect(response.status).toBe(200);
    expect(await response.text()).toBe(
      `<html><head>${AddonsConstants.scriptAddons}</head><body></body></html>`,
    );
  });

  it("injects project/version metadata", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/" })
      .reply(200, "<html><head></head><body></body></html>", {
        headers: {
          "Content-type": "text/html",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": false,
          "X-RTD-Project": "test-builds",
          "X-RTD-Version": "latest",
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/",
    );
    expect(response.status).toBe(200);
    expect(await response.text())
      .to.contain(AddonsConstants.scriptAddons)
      .to.contain(
        `<meta name="readthedocs-project-slug" content="test-builds" />`,
      )
      .to.contain(`<meta name="readthedocs-version-slug" content="latest" />`);
  });

  it("removes old flyout doc embed assets", async () => {
    const scripts = [
      `<script src="/_/static/javascript/readthedocs-analytics.js"></script>`,
      `<script src="/_/static/javascript/readthedocs-doc-embed.js"></script>`,
      `<script src="/_/static/core/js/readthedocs-doc-embed.js"></script>`,
      `<script src="https://assets.readthedocs.org/static/javascript/readthedocs-analytics.js"></script>`,
      `<script src="https://assets.readthedocs.org/static/javascript/readthedocs-doc-embed.js"></script>`,
      `<script src="https://assets.readthedocs.org/static/core/js/readthedocs-doc-embed.js"></script>`,
    ];
    const links = [
      `<link rel="stylesheet" href="/_/static/css/readthedocs-doc-embed.css" />`,
      `<link rel="stylesheet" href="https://assets.readthedocs.org/static/css/readthedocs-doc-embed.css" />`,
      `<link rel="stylesheet" href="https://assets.readthedocs.org/static/css/badge_only.css" />`,
      `<link rel="stylesheet" href="/_/static/css/badge_only.css" />`,
    ];
    const elements = [
      `<div role="main"><div x-ref="outer"><div class="admonition warning" x-ref="inner"></div></div></div>`,
      `<div role="main" x-ref="outer-furo"><div class="admonition warning" x-ref="inner-furo"></div></div>`,
      `<div id="main-content"><div><div><article x-ref="outer-book"><div class="admonition warning" x-ref="inner-book"></div></article></div></div></div>`,
      `<div class="rst-versions" x-ref="flyout"></div>`,
    ];

    // Ensure we're testing all of the removals
    expect(scripts.length).toBe(AddonsConstants.removalScripts.length);
    expect(links.length).toBe(AddonsConstants.removalLinks.length);
    expect(elements.length).toBe(AddonsConstants.removalElements.length);

    // Test all removals at once
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/" })
      .reply(
        200,
        `
        <html>
          <head>
            ${scripts.join("")}
            ${links.join("")}
            <script src="https://example.com"></script>
          </head>
          <body>
            ${elements.join("")}
          </body>
        </html>`,
        {
          headers: {
            "Content-type": "text/html",
            "X-RTD-Force-Addons": true,
            "X-RTD-Hosting-Integrations": false,
          },
        },
      );
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/",
    );
    expect(response.status).toBe(200);
    const matcher = expect(await response.text());
    matcher.to.contain(AddonsConstants.scriptAddons);
    // Ensure matches aren't too aggressive
    matcher.to.contain(`<script src="https://example.com"></script>`);

    // Make sure scripts and linker were removed
    for (const script of scripts) {
      matcher.to.not.contain(script);
    }
    for (const link of links) {
      matcher.to.not.contain(link);
    }

    // Make sure elements were removed, using extra attrs because the whole
    // string is not removed
    matcher.to.contain(`x-ref="outer"`);
    matcher.to.not.contain(`x-ref="inner"`);
    matcher.to.contain(`x-ref="outer-furo"`);
    matcher.to.not.contain(`x-ref="inner-furo"`);
    matcher.to.contain(`x-ref="outer-book"`);
    matcher.to.not.contain(`x-ref="inner-book"`);
    matcher.to.not.contain(`x-ref="flyout"`);
  });

  it("skips content types other than HTML", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/_static/foo.js" })
      .reply(200, "console.log(true);", {
        headers: {
          "Content-type": "application/javascript",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": true,
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/_static/foo.js",
    );
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("console.log(true);");
    expect(response.headers.get("Content-type")).toBe("application/javascript");
  });

  it("handles searchtools.js", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/_static/searchtools.js" })
      .reply(200, AddonsConstants.replacements.searchtools.pattern, {
        headers: {
          "Content-type": "application/javascript",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": true,
          "X-RTD-Test-Passthrough": 42,
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/_static/searchtools.js",
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-type")).toBe("application/javascript");
    expect(response.headers.get("X-RTD-Test-Passthrough")).toBe("42");
    expect(await response.text()).toContain(
      AddonsConstants.replacements.searchtools.replacement,
    );
  });

  it("handles error gracefully", async () => {
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/" })
      .reply(200, `<html><head></head><body></body></html>`, {
        headers: {
          "Content-type": "text/html",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": false,
          "X-RTD-Test-Passthrough": 42,
          "X-RTD-Throw-Error": true,
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/",
    );
    expect(response.status).toBe(200);
    // Expect the original response and headers
    expect(await response.text()).toBe(
      `<html><head></head><body></body></html>`,
    );
    expect(response.headers.get("X-RTD-Test-Passthrough")).toBe("42");
  });

  it("handles binary content", async () => {
    // It's not clear if this test is helpful. Some operations that were
    // previously using `Response.text()` were choking on the binary data. This
    // test may not be catching those points anymore.
    const binaryData = Buffer.from([
      137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82,
    ]);
    fetchMock
      .get("http://test-builds.devthedocs.org")
      .intercept({ path: "/en/latest/_/static/images/test.png" })
      .reply(200, binaryData, {
        headers: {
          "Content-type": "image/png",
          "X-RTD-Force-Addons": true,
          "X-RTD-Hosting-Integrations": false,
          "X-RTD-Project": "test-builds",
          "X-RTD-Version": "latest",
        },
      });
    let response = await SELF.fetch(
      "http://test-builds.devthedocs.org/en/latest/_/static/images/test.png",
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("image/png");
    const buffer = await response.arrayBuffer();
    expect(buffer.byteLength).toBe(16);
    expect(new Uint8Array(buffer)).toEqual(new Uint8Array(binaryData));
  });
});
