try:
    import flask
    print("flask OK")
    import flask_sqlalchemy
    print("flask_sqlalchemy OK")
    import flask_login
    print("flask_login OK")
    import flask_cors
    print("flask_cors OK")
    import dotenv
    print("dotenv OK")
    import google.generativeai
    print("google.generativeai OK")
    import gtts
    print("gtts OK")
except ImportError as e:
    print(f"Import failed: {e}")
