📸 MediaVault: AI-Powered Media Intelligence
[Screenshot Placeholder - Coming Soon]

📄 Overview
MediaVault is a professional-grade photo and video management system that transforms a static gallery into an intelligent, searchable database. By integrating Google Gemini AI, the application automatically analyzes, describes, and tags uploaded images upon arrival.

Built with a robust Python backend, MediaVault serves as a high-performance portfolio for creative assets, featuring a custom Role-Based Access Control (RBAC) system to maintain data integrity while allowing public walkthroughs.

🌐 Live Demo
Live URL: https://my-media-vault-yhpp.onrender.com

Guest Access: * Username: guest Password: guest123

(Note: Guest mode is view-only to showcase features without modifying the live database.)

🛠️ Tech Stack
Intelligence: Google Gemini Pro Vision API

Backend: FastAPI (Python 3.14+)

Database: SQLAlchemy ORM with SQLite

Frontend: Jinja2 Templates & Tailwind CSS

Authentication: Cookie-based sessions with password hashing (Passlib/Bcrypt)

Environment: python-dotenv for secure API key management

Deployment: Render

✨ Key Engineering Features
AI Vision Analysis: Leverages Google Gemini to automatically generate descriptive captions and metadata tags for every upload.

Dual-Role Authentication: Custom middleware logic to distinguish between Admin (Full CRUD) and Guest (Read-Only) identities using secure HTTP-only cookies.

Modular Architecture: Follows a clean design pattern separating AI processing logic, database management, and UI rendering.

Automated Metadata Extraction: Systematically extracts file types, sizes, and timestamps during the ingestion process.

Relational Integrity: Implements a structured SQL schema to ensure reliable media-to-tag relationships.

⚙️ Local Setup
Clone the repository:

1. git clone https://github.com/github4eri/MediaVault
Install dependencies:

2. pip install -r requirements.txt

3. Environment Variables: Create a .env file and add your GEMINI_API_KEY, ADMIN_PASSWORD, and GUEST_PASSWORD.

4. Start the development server: uvicorn main:app --reload
