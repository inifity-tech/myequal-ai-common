"""Sample utility functions for testing package integration."""


def hello_world() -> str:
    """Return a hello world message.
    
    Returns:
        str: A friendly greeting message
    """
    return "Hello World from MyEqual AI Common Library!"


def hello_name(name: str) -> str:
    """Return a personalized hello message.
    
    Args:
        name: The name to greet
        
    Returns:
        str: A personalized greeting message
    """
    return f"Hello {name} from MyEqual AI Common Library!"