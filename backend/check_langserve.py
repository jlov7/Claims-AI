import langserve
import sys

print(f"LangServe version: {langserve.__version__}")
print(f"Has frontend attribute: {hasattr(langserve, 'frontend')}")
if hasattr(langserve, 'frontend'):
    print(f"langserve.frontend path: {langserve.frontend.__path__}")
    print(f"dir(langserve.frontend): {dir(langserve.frontend)}")
    print(f"Has create_frontend in langserve.frontend: {hasattr(langserve.frontend, 'create_frontend')}")

print(f"sys.path: {sys.path}")
print(f"langserve path: {langserve.__path__}")

# Try to import create_frontend directly
try:
    from langserve.frontend import create_frontend
    print("Successfully imported create_frontend from langserve.frontend")
    print(f"create_frontend: {create_frontend}")
except ImportError as e:
    print(f"Failed to import create_frontend: {e}") 