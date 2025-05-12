.PHONY: arch-diagram
arch-diagram:
	@echo "Generating architecture.svg from architecture.md..."
	npx @mermaid-js/mermaid-cli -i docs/architecture.md -o docs/architecture.svg 