import sys
print(f"Python sys.path: {sys.path}")

try:
    import langserve
    print(f"Successfully imported langserve.")
    print(f"langserve.__path__: {getattr(langserve, '__path__', 'N/A')}")
    print(f"dir(langserve): {dir(langserve)}")
    
    try:
        import langserve.playground as lsp
        print("Successfully imported langserve.playground")
        print(f"langserve.playground.__path__: {getattr(lsp, '__path__', 'N/A')}")
        print(f"dir(langserve.playground): {dir(lsp)}")
    except ImportError as e_playground:
        print(f"Failed to import langserve.playground: {e_playground}")
    except Exception as e_playground_other:
        print(f"Other error importing langserve.playground: {e_playground_other}")

    try:
        import langserve.frontend
        print("Successfully imported langserve.frontend (in docker_import_test.py)")
    except ImportError as e_frontend:
        print(f"Failed to import langserve.frontend (in docker_import_test.py): {e_frontend}")

except ImportError as e_main:
    print(f"Failed to import langserve (main package): {e_main}")
except Exception as e_main_other:
    print(f"Other error importing langserve (main package): {e_main_other}") 