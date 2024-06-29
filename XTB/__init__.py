VERSION="1.0.0"
WRAPPER="2.5.0"

__all__ = ['Wrapper']

dependencies = []

# Optional: Dependency check
try:
    import some_dependency
except ImportError:
    raise ImportError("This package requires 'some_dependency'. Please install it first.")
