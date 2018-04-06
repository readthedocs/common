#      ___          ___          ___          ___          ___          ___
#     /\  \        /\  \        /\__\        /\__\        /\  \        /\__\
#    /::\  \      /::\  \      /::|  |      /::|  |      /::\  \      /::|  |
#   /:/\:\  \    /:/\:\  \    /:|:|  |     /:|:|  |     /:/\:\  \    /:|:|  |
#  /:/  \:\  \  /:/  \:\  \  /:/|:|__|__  /:/|:|__|__  /:/  \:\  \  /:/|:|  |__
# /:/__/ \:\__\/:/__/ \:\__\/:/ |::::\__\/:/ |::::\__\/:/__/ \:\__\/:/ |:| /\__\
# \:\  \  \/__/\:\  \ /:/  /\/__/~~/:/  /\/__/~~/:/  /\:\  \ /:/  /\/__|:|/:/  /
#  \:\  \       \:\  /:/  /       /:/  /       /:/  /  \:\  /:/  /     |:/:/  /
#   \:\  \       \:\/:/  /       /:/  /       /:/  /    \:\/:/  /      |::/  /
#    \:\__\       \::/  /       /:/  /       /:/  /      \::/  /       /:/  /
#     \/__/        \/__/        \/__/        \/__/        \/__/        \/__/
#

# Default
default: link pre-commit

# Config rules
CONFIG = \
	prospector.yml \
	tasks.py

CONFIG_HIDDEN = \
	.eslintrc \
	.flake8 \
	.isort.cfg \
	.pep8 \
	.pre-commit-config.yaml \
	.style.yapf \

CONFIG_ALL = $(CONFIG) $(CONFIG_HIDDEN)


.PHONY: link default pre-commit ignore

link: $(CONFIG_ALL)

$(CONFIG): %: common/%
	[ -e "$@" ] || (ln -s $? $@ && git add $@)

$(CONFIG_HIDDEN): .%: common/%
	[ -e "$@" ] || (ln -s $? $@ && git add $@)

pre-commit:
	pre-commit clean
