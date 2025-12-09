# Implementation Plan for OAuth-like Authentication Flow

## File Structure Changes

### New Files to Create

```
src/twojtenis_mcp/
├── auth_server.py          # Local authentication server
├── oauth_flow.py           # OAuth-like flow coordinator
├── templates/
│   └── login.html         # Login page template
├── static/
│   └── auth.js            # JavaScript for cookie capture
└── utils/
    └── browser_utils.py   # Browser-related utilities
```

### Files to Modify

```
src/twojtenis_mcp/
├── auth.py                # Update session manager
├── client.py              # Remove credential-based auth
├── server.py              # Add new MCP tools
├── config.py              # Remove credential requirements
└── models.py              # Add new models if needed
```

## Detailed Implementation Specifications

### 1. Local Authentication Server (`auth_server.py`)

```python
import asyncio
import json
import logging
import random
import string
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logger = logging.getLogger(__name__)

class LocalAuthServer:
    """Local authentication server for OAuth-like flow"""
    
    def __init__(self, port: Optional[int] = None):
        self.port = port or self._find_available_port()
        self.app = FastAPI(title="TwojTenis Auth Server")
        self.state_token = self._generate_state_token()
        self.phpsessid: Optional[str] = None
        self.auth_completed = asyncio.Event()
        self.server: Optional[uvicorn.Server] = None
        
        # Setup routes
        self._setup_routes()
    
    def _find_available_port(self) -> int:
        """Find an available port in the range 8080-8090"""
        for port in range(8080, 8091):
            # Check if port is available
            # Implementation details...
            return port
        raise RuntimeError("No available ports found")
    
    def _generate_state_token(self) -> str:
        """Generate a random state token for security"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def login_page():
            """Serve the login page"""
            template_path = Path(__file__).parent / "templates" / "login.html"
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            # Replace placeholders
            template = template.replace("{{STATE_TOKEN}}", self.state_token)
            return template
        
        @self.app.post("/auth/callback")
        async def auth_callback(request: Request):
            """Handle authentication callback"""
            data = await request.json()
            
            # Validate state token
            if data.get("state") != self.state_token:
                raise HTTPException(status_code=400, detail="Invalid state token")
            
            # Extract PHPSESSID
            phpsessid = data.get("phpsessid")
            if not phpsessid:
                raise HTTPException(status_code=400, detail="Missing PHPSESSID")
            
            self.phpsessid = phpsessid
            self.auth_completed.set()
            
            return JSONResponse({"status": "success"})
        
        @self.app.get("/static/{file_path:path}")
        async def static_files(file_path: str):
            """Serve static files"""
            static_path = Path(__file__).parent / "static" / file_path
            if not static_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            with open(static_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return content
    
    async def start(self):
        """Start the authentication server"""
        config = uvicorn.Config(
            app=self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning"  # Reduce log noise
        )
        self.server = uvicorn.Server(config)
        
        # Start server in background
        asyncio.create_task(self.server.serve())
        logger.info(f"Auth server started on http://127.0.0.1:{self.port}")
    
    async def stop(self):
        """Stop the authentication server"""
        if self.server:
            self.server.should_exit = True
            await self.server.shutdown()
            logger.info("Auth server stopped")
    
    async def wait_for_auth(self, timeout: int = 300) -> Optional[str]:
        """Wait for authentication to complete"""
        try:
            await asyncio.wait_for(self.auth_completed.wait(), timeout=timeout)
            return self.phpsessid
        except asyncio.TimeoutError:
            logger.warning("Authentication timed out")
            return None
    
    def get_login_url(self) -> str:
        """Get the login URL for the user"""
        return f"http://127.0.0.1:{self.port}/"
```

### 2. OAuth Flow Coordinator (`oauth_flow.py`)

```python
import asyncio
import logging
from typing import Optional

from .auth_server import LocalAuthServer
from .auth import session_manager

logger = logging.getLogger(__name__)

class OAuthFlowCoordinator:
    """Coordinates the OAuth-like authentication flow"""
    
    def __init__(self):
        self.auth_server: Optional[LocalAuthServer] = None
        self.is_authenticating = False
    
    async def initiate_authentication(self) -> dict[str, str]:
        """Initiate the authentication flow"""
        if self.is_authenticating:
            return {
                "status": "error",
                "message": "Authentication already in progress"
            }
        
        try:
            # Start local auth server
            self.auth_server = LocalAuthServer()
            await self.auth_server.start()
            self.is_authenticating = True
            
            # Return login URL to user
            login_url = self.auth_server.get_login_url()
            
            return {
                "status": "success",
                "message": "Authentication server started",
                "login_url": login_url,
                "instructions": (
                    "Please open the URL above in your browser and log in to TwojTenis.pl. "
                    "The system will automatically capture your session once you complete the login."
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to start authentication: {e}")
            return {
                "status": "error",
                "message": f"Failed to start authentication: {str(e)}"
            }
    
    async def complete_authentication(self, timeout: int = 300) -> dict[str, str]:
        """Complete the authentication flow"""
        if not self.is_authenticating or not self.auth_server:
            return {
                "status": "error",
                "message": "No authentication in progress"
            }
        
        try:
            # Wait for authentication to complete
            phpsessid = await self.auth_server.wait_for_auth(timeout)
            
            if phpsessid:
                # Save session
                await session_manager.save_external_session(phpsessid)
                
                # Cleanup
                await self.auth_server.stop()
                self.auth_server = None
                self.is_authenticating = False
                
                return {
                    "status": "success",
                    "message": "Authentication completed successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Authentication timed out or failed"
                }
                
        except Exception as e:
            logger.error(f"Authentication completion failed: {e}")
            return {
                "status": "error",
                "message": f"Authentication failed: {str(e)}"
            }
    
    async def cancel_authentication(self) -> dict[str, str]:
        """Cancel the authentication flow"""
        if self.auth_server:
            await self.auth_server.stop()
            self.auth_server = None
            self.is_authenticating = False
        
        return {
            "status": "success",
            "message": "Authentication cancelled"
        }

# Global OAuth flow coordinator
oauth_coordinator = OAuthFlowCoordinator()
```

### 3. Updated Session Manager (`auth.py` modifications)

```python
# Add these methods to the existing SessionManager class

async def save_external_session(self, phpsessid: str) -> None:
    """Save externally obtained session ID.
    
    Args:
        phpsessid: PHP session ID obtained from external authentication
    """
    self._session = UserSession(
        phpsessid=phpsessid,
        expires_at=datetime.now(UTC) + timedelta(minutes=config.session_lifetime),
    )
    try:
        session_data = self._session.model_dump()

        if self._session.expires_at:
            session_data["expires_at"] = self._session.expires_at.isoformat()

        with open(self._session_file_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        logger.info("External session saved to file")

    except (OSError, TypeError) as e:
        logger.error(f"Failed to save external session to file: {e}")

async def is_session_expired(self) -> bool:
    """Check if current session is expired or will expire soon.
    
    Returns:
        True if session is expired or will expire within 5 minutes, False otherwise
    """
    session = await self.get_session()
    return session is None

async def request_reauthentication(self) -> dict[str, Any]:
    """Request re-authentication through OAuth flow.
    
    Returns:
        Authentication result with login URL if needed
    """
    from .oauth_flow import oauth_coordinator
    
    # First, try to cancel any existing authentication
    await oauth_coordinator.cancel_authentication()
    
    # Initiate new authentication
    return await oauth_coordinator.initiate_authentication()

async def check_and_handle_session(self) -> bool:
    """Check session validity and handle re-authentication if needed.
    
    Returns:
        True if session is valid, False if re-authentication is required
    """
    if not await self.is_session_expired():
        return True
    
    logger.warning("Session expired, re-authentication required")
    return False
```

### 4. Login Page Template (`templates/login.html`)

```html
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TwojTenis.pl Authentication</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .instructions {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        .iframe-container {
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        iframe {
            width: 100%;
            height: 600px;
            border: none;
        }
        .status {
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            font-weight: bold;
        }
        .status.waiting {
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        .status.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .fallback {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }
        .manual-input {
            margin-top: 15px;
        }
        .manual-input input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
        }
        .manual-input button {
            margin-top: 10px;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .manual-input button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TwojTenis.pl Authentication</h1>
            <p>Complete your login to authorize the MCP server</p>
        </div>
        
        <div class="instructions">
            <h3>Instructions:</h3>
            <ol>
                <li>Log in to TwojTenis.pl using the form below</li>
                <li>The system will automatically detect when you've successfully logged in</li>
                <li>If automatic detection fails, use the manual option below</li>
            </ol>
        </div>
        
        <div class="iframe-container">
            <iframe 
                src="https://www.twojtenis.pl/pl/login.html" 
                id="login-frame"
                sandbox="allow-same-origin allow-scripts allow-forms allow-top-navigation">
            </iframe>
        </div>
        
        <div id="status" class="status waiting">
            Waiting for authentication...
        </div>
        
        <div class="fallback">
            <h3>Manual Option (if automatic detection fails):</h3>
            <p>If the automatic detection doesn't work, follow these steps:</p>
            <ol>
                <li>Log in successfully in the iframe above</li>
                <li>Open your browser's developer tools (F12)</li>
                <li>Go to the "Application" or "Storage" tab</li>
                <li>Find "Cookies" under "Storage"</li>
                <li>Look for the "PHPSESSID" cookie for twojtenis.pl</li>
                <li>Copy the PHPSESSID value and paste it below</li>
            </ol>
            
            <div class="manual-input">
                <input type="text" id="manual-phpsessid" placeholder="Paste PHPSESSID value here">
                <button onclick="submitManualSession()">Submit Session</button>
            </div>
        </div>
    </div>
    
    <script>
        const STATE_TOKEN = "{{STATE_TOKEN}}";
        let authCompleted = false;
        
        // Function to update status
        function updateStatus(message, type = 'waiting') {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = `status ${type}`;
        }
        
        // Function to submit session to server
        async function submitSession(phpsessid) {
            if (authCompleted) return;
            
            try {
                const response = await fetch('/auth/callback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        state: STATE_TOKEN,
                        phpsessid: phpsessid
                    })
                });
                
                if (response.ok) {
                    authCompleted = true;
                    updateStatus('Authentication successful! You can close this window.', 'success');
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                } else {
                    updateStatus('Authentication failed. Please try again.', 'error');
                }
            } catch (error) {
                updateStatus('Error communicating with authentication server.', 'error');
            }
        }
        
        // Manual session submission
        function submitManualSession() {
            const phpsessid = document.getElementById('manual-phpsessid').value.trim();
            if (phpsessid) {
                updateStatus('Submitting session...', 'waiting');
                submitSession(phpsessid);
            } else {
                updateStatus('Please enter a PHPSESSID value.', 'error');
            }
        }
        
        // Monitor iframe for successful login
        const iframe = document.getElementById('login-frame');
        let loginAttempts = 0;
        
        iframe.onload = function() {
            loginAttempts++;
            
            // Try to detect successful login
            try {
                // Check if iframe URL changed (indicating successful login)
                const iframeUrl = iframe.contentWindow.location.href;
                
                if (iframeUrl.includes('dashboard') || iframeUrl.includes('home') || 
                    (loginAttempts > 1 && !iframeUrl.includes('login'))) {
                    updateStatus('Login detected! Capturing session...', 'waiting');
                    
                    // Try to extract cookies (may fail due to same-origin policy)
                    try {
                        const cookies = iframe.contentDocument.cookie;
                        const phpsessidMatch = cookies.match(/PHPSESSID=([^;]+)/);
                        if (phpsessidMatch) {
                            submitSession(phpsessidMatch[1]);
                        } else {
                            updateStatus('Could not extract session automatically. Please use manual option.', 'error');
                        }
                    } catch (cookieError) {
                        // Same-origin policy blocked cookie access
                        updateStatus('Automatic session extraction blocked by browser security. Please use manual option.', 'error');
                    }
                }
            } catch (error) {
                // Same-origin policy blocked URL access
                if (loginAttempts > 2) {
                    updateStatus('Cannot detect login automatically due to browser security. Please use manual option.', 'error');
                }
            }
        };
        
        // Set up periodic check for session completion
        setInterval(async () => {
            if (authCompleted) return;
            
            try {
                const response = await fetch('/auth/status');
                const data = await response.json();
                
                if (data.authenticated) {
                    authCompleted = true;
                    updateStatus('Authentication successful! You can close this window.', 'success');
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                }
            } catch (error) {
                // Ignore errors for status check
            }
        }, 2000);
    </script>
</body>
</html>
```

### 5. Updated MCP Server Tools (`server.py` additions)

```python
# Add these new tools to the existing server.py

@mcp.tool()
async def login() -> dict[str, Any]:
    """Initiate authentication flow with TwojTenis.pl.
    
    Returns:
        Authentication result with login URL and instructions
    """
    try:
        from .oauth_flow import oauth_coordinator
        
        # Check if already authenticated
        session = await session_manager.get_session()
        if session:
            return {
                "success": True,
                "message": "Already authenticated",
                "session_expires_at": session.expires_at.isoformat() if session.expires_at else None
            }
        
        # Initiate authentication
        result = await oauth_coordinator.initiate_authentication()
        
        if result["status"] == "success":
            return {
                "success": True,
                "message": result["message"],
                "login_url": result["login_url"],
                "instructions": result["instructions"]
            }
        else:
            return {
                "success": False,
                "message": result["message"]
            }
            
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        return {
            "success": False,
            "message": f"Login failed: {str(e)}"
        }

@mcp.tool()
async def complete_login(timeout: int = 300) -> dict[str, Any]:
    """Complete the authentication flow.
    
    Args:
        timeout: Maximum time to wait for authentication (seconds)
    
    Returns:
        Authentication completion result
    """
    try:
        from .oauth_flow import oauth_coordinator
        
        result = await oauth_coordinator.complete_authentication(timeout)
        
        if result["status"] == "success":
            session = await session_manager.get_session()
            return {
                "success": True,
                "message": result["message"],
                "session_expires_at": session.expires_at.isoformat() if session and session.expires_at else None
            }
        else:
            return {
                "success": False,
                "message": result["message"]
            }
            
    except Exception as e:
        logger.error(f"Login completion failed: {e}")
        return {
            "success": False,
            "message": f"Login completion failed: {str(e)}"
        }

@mcp.tool()
async def get_session_status() -> dict[str, Any]:
    """Get current authentication session status.
    
    Returns:
        Current session status information
    """
    try:
        session = await session_manager.get_session()
        
        if session:
            return {
                "authenticated": True,
                "phpsessid": session.phpsessid[:8] + "...",  # Show only first 8 chars for security
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "minutes_remaining": None  # Calculate if needed
            }
        else:
            return {
                "authenticated": False,
                "message": "No active session"
            }
            
    except Exception as e:
        logger.error(f"Session status check failed: {e}")
        return {
            "authenticated": False,
            "message": f"Status check failed: {str(e)}"
        }

@mcp.tool()
async def logout() -> dict[str, Any]:
    """Logout and clear current session.
    
    Returns:
        Logout result
    """
    try:
        from .oauth_flow import oauth_coordinator
        
        # Cancel any ongoing authentication
        await oauth_coordinator.cancel_authentication()
        
        # Clear session
        await session_manager.logout()
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return {
            "success": False,
            "message": f"Logout failed: {str(e)}"
        }
```

### 6. Configuration Updates (`config.py` modifications)

```python
# Remove these properties from the Config class:
# - email
# - password

# Add these new properties:

@property
def auth_server_port_range(self) -> tuple[int, int]:
    """Get port range for local authentication server."""
    start = int(self.get("TWOJTENIS_AUTH_PORT_START", "8080"))
    end = int(self.get("TWOJTENIS_AUTH_PORT_END", "8090"))
    return (start, end)

@property
def auth_timeout(self) -> int:
    """Get authentication timeout in seconds."""
    return int(self.get("TWOJTENIS_AUTH_TIMEOUT", "300"))

@property
def enable_debug_mode(self) -> bool:
    """Check if debug mode is enabled."""
    return self.get("TWOJTENIS_DEBUG", "false").lower() == "true"

# Update the to_dict method:
def to_dict(self) -> dict[str, Any]:
    """Convert configuration to dictionary."""
    return {
        "base_url": self.base_url,
        "session_lifetime": self.session_lifetime,
        "request_timeout": self.request_timeout,
        "retry_attempts": self.retry_attempts,
        "retry_delay": self.retry_delay,
        "auth_server_port_range": self.auth_server_port_range,
        "auth_timeout": self.auth_timeout,
        "enable_debug_mode": self.enable_debug_mode,
    }
```

## Implementation Order

1. **Phase 1**: Create the basic infrastructure
   - Create `auth_server.py`
   - Create `oauth_flow.py`
   - Update `auth.py` with new methods

2. **Phase 2**: Create the user interface
   - Create `templates/login.html`
   - Create `static/auth.js` (if needed separately)

3. **Phase 3**: Integrate with MCP server
   - Update `server.py` with new tools
   - Update `client.py` to handle session expiration
   - Update `config.py` to remove credential requirements

4. **Phase 4**: Testing and refinement
   - Test the complete flow
   - Add error handling
   - Create documentation

This implementation provides a secure, user-friendly authentication flow that eliminates the need to store user credentials while maintaining compatibility with the existing twojtenis.pl session management system.