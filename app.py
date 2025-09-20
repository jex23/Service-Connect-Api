from flask import Flask
from flask_restx import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

# Configuration
db_user = os.getenv('DB_USER', 'james23')
db_password = quote_plus(os.getenv('DB_PASSWORD', 'J@mes2410117'))
db_host = os.getenv('DB_HOST', '179.61.246.136')
db_port = os.getenv('DB_PORT', '3306')
db_name = os.getenv('DB_NAME', 'service_connect')

# R2 Configuration
app.config['R2_ACCESS_KEY'] = os.getenv('r2_access_key')
app.config['R2_SECRET_KEY'] = os.getenv('r2_secret_key')
app.config['R2_ENDPOINT'] = os.getenv('r2_endpoint')
app.config['R2_BUCKET_NAME'] = os.getenv('r2_bucket_name')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
# JWT Header configuration for Swagger compatibility
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# Initialize extensions
from models import db
db.init_app(app)
jwt = JWTManager(app)

# JWT Error handlers for better debugging
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {'msg': 'Token has expired'}, 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return {'msg': f'Invalid token: {error}'}, 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return {'msg': f'Missing authorization token: {error}'}, 401

# Custom function to handle request debugging and Bearer prefix injection
from flask import request

@app.before_request
def handle_authorization():
    # Handle Bearer prefix injection for Swagger UI
    if request.path.startswith('/api/') and request.headers.get('Authorization'):
        auth_header = request.headers.get('Authorization')

        # If Authorization header exists but doesn't start with "Bearer "
        if auth_header and not auth_header.startswith('Bearer '):
            # Check if it's a JWT token (starts with 'eyJ')
            if auth_header.startswith('eyJ'):
                # Add Bearer prefix by modifying the WSGI environ directly
                new_header = f"Bearer {auth_header}"
                # Convert header name to CGI format
                request.environ['HTTP_AUTHORIZATION'] = new_header
                print(f"DEBUG: Auto-added Bearer prefix: {new_header[:50]}...")

    # Debug logging for adminprovider endpoints
    if request.path.startswith('/api/') and ('adminprovider' in request.path or 'categories' in request.path):
        print(f"DEBUG: Request to {request.path}")
        print(f"DEBUG: Headers: {dict(request.headers)}")
        print(f"DEBUG: Authorization header: {request.headers.get('Authorization', 'NOT FOUND')}")
        print(f"DEBUG: Method: {request.method}")
        print("---")

# Initialize Flask-RESTX with authentication
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Enter: Bearer <your-jwt-token>. Example: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
    }
}

api = Api(
    app,
    version='1.0',
    title='Service Connect API',
    description='''API for Service Connect platform with user and provider authentication.

## Authentication
This API uses JWT (JSON Web Tokens) for authentication. To access protected endpoints:

1. **Login**: Use `/api/auth/login` or `/api/auth/provider/login` to get your access token
2. **Authorize**: Click the "Authorize" button below and enter **ONLY the token** (no Bearer prefix needed)
3. **Access**: All protected endpoints will now use your authentication token

### Quick Start:
1. Register or login to get your JWT token
2. Copy the token from the response (just the token part)
3. Click "Authorize" button and paste only the token
4. The system will automatically add "Bearer " prefix

### Important Notes:
- ✅ Enter only the token: `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`
- ❌ Don't enter: `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`
- The "Bearer " prefix is added automatically by the system

### Token Example:
```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VyX3R5cGUiOiJ1c2VyIiwiaWF0IjoxNjM5NzMxMjAwfQ.signature
```''',
    doc='/docs/',
    authorizations=authorizations
)

# Import and register namespaces
from routes.auth import auth_ns
from routes.users import users_ns
from routes.providers import providers_ns
from routes.chat import chat_ns

api.add_namespace(auth_ns, path='/api/auth')
api.add_namespace(users_ns, path='/api/users')
api.add_namespace(providers_ns, path='/api/providers')
api.add_namespace(chat_ns, path='/api/chat')

if __name__ == '__main__':
    try:
        print("Starting Service Connect API...")
        print(f"Database URI: mysql+pymysql://{db_user}:***@{db_host}:{db_port}/{db_name}")
        
        # Test database connection
        with app.app_context():
            db.create_all()
            print("Database tables created successfully!")
            
        print("Starting Flask server on http://0.0.0.0:9078")
        print("API Documentation available at: http://localhost:9078/docs/")
        app.run(debug=True, host='0.0.0.0', port=9078)
        
    except Exception as e:
        print(f"Error starting application: {e}")
        print("\nRunning without database connection for API testing...")
        print("API Documentation available at: http://localhost:9078/docs/")
        app.run(debug=True, host='0.0.0.0', port=9078)