# =============================================================================
# Makefile help function
#
# Usage:
#   awk -f scripts/help.awk $(MAKEFILE_LIST)
#
# Function:
#   Parses the Makefile for target descriptions and section headers.
#   - Targets: target: ## description
#   - Sections: ## Section Name ##
# =============================================================================

BEGIN {
    FS = ":.*?## "
    # text attributes
    text_bold = "\033[1m"
    text_cyan = "\033[36m"
    text_reset = "\033[0m"
}

/^## .* ##$/ {
    gsub(/^## | ##$/, "", $0)
    printf "\n%s%s%s\n", text_bold, $0, text_reset
    next
}

/^[a-zA-Z_-]+:.*?## .*$/ {
    printf "%s%-30s%s %s\n", text_cyan, $1, text_reset, $2
}
