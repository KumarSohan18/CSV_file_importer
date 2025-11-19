# Product Importer Application

A scalable web application for importing and managing products from CSV files, built with FastAPI, Celery, and PostgreSQL.

## Features

### STORY 1 - File Upload via UI
- Upload large CSV files (up to 500,000 products) through the web interface
- Real-time progress tracking using Server-Sent Events (SSE)
- Automatic duplicate handling based on case-insensitive SKU matching
- Asynchronous processing using Celery to handle long-running operations

### STORY 1A - Upload Progress Visibility
- Real-time progress bar and percentage display
- Status messages (Parsing CSV, Validating, Import Complete)
- Error handling with clear failure messages
- Retry capability

### STORY 2 - Product Management UI
- View products with pagination (50 per page)
- Filter by SKU, name, description, and active status
- Create new products via modal form
- Update existing products inline
- Delete individual products with confirmation

### STORY 3 - Bulk Delete
- Delete all products with a single action
- Confirmation dialog to prevent accidental deletion
- Success/failure notifications

### STORY 4 - Webhook Configuration
- Add, edit, and delete webhooks via UI
- Configure webhook URL, event type, and enable/disable status
- Test webhooks with response code and response time display
- Automatic webhook triggering on product events:
  - `product.created`
  - `product.updated`
  - `product.deleted`
  - `product.bulk_import`
  - `product.bulk_delete`

## Tech Stack

- **Web Framework**: FastAPI
- **Async Task Queue**: Celery with Redis
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Real-time Updates**: Server-Sent Events (SSE)

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database connection and session
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── products.py         # Product CRUD endpoints
│   │   ├── upload.py           # File upload endpoint
│   │   ├── webhooks.py         # Webhook management endpoints
│   │   └── progress.py         # Progress tracking (SSE)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_processor.py    # CSV parsing and processing logic
│   │   └── webhook_service.py  # Webhook triggering logic
│   └── tasks/
│       ├── __init__.py
│       └── import_tasks.py     # Celery tasks for async processing
├── static/
│   ├── index.html              # Main UI
│   ├── css/
│   │   └── style.css           # Styling
│   └── js/
│       └── app.js              # Frontend logic
├── celery_app.py               # Celery configuration
├── requirements.txt            # Python dependencies
├── Procfile                    # Heroku deployment config
├── runtime.txt                 # Python version
└── README.md                   # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- pip

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fulfil-tech-assessment
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis URLs
   ```

5. **Set up PostgreSQL database**
   ```bash
   createdb productdb
   # Update DATABASE_URL in .env
   ```

6. **Start Redis**
   ```bash
   redis-server
   # Or use Docker: docker run -d -p 6379:6379 redis
   ```

7. **Initialize database**
   The application will automatically create tables on first run.

8. **Start Celery worker** (in a separate terminal)
   ```bash
   celery -A celery_app worker --loglevel=info --pool=solo
   ```

9. **Start FastAPI server** (in one terminal)
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

10. **Start Frontend server** (in another terminal)
    Option 1 - Using Python:
    ```bash
    python serve_frontend.py
    ```
    
    Option 2 - Using Node.js (if you have it installed):
    ```bash
    npm install -g http-server
    http-server static -p 3000 -c-1 --cors
    ```
    
    Option 3 - Using npx (no installation needed):
    ```bash
    npx http-server static -p 3000 -c-1 --cors
    ```

11. **Access the application**
    - Frontend: Open http://localhost:3000 in your browser
    - Backend API: http://localhost:8000
    - API Docs: http://localhost:8000/docs

### Frontend (Next.js)

```
frontend/
├── src/app/page.tsx           # Main UI (upload, products, webhooks)
├── src/app/globals.css        # Styling tokens
├── .env.local.example         # API base URL sample
└── package.json               # Next.js scripts
```

Available scripts (run inside `frontend/`):

```bash
npm run dev      # local development (http://localhost:3000)
npm run build    # production build
npm start        # run built app
```

Set `NEXT_PUBLIC_API_BASE` in `.env.local` (see example file). For local dev it should point to `http://localhost:8000/api`.

## Deployment

### Heroku Deployment

1. **Install Heroku CLI** and login
   ```bash
   heroku login
   ```

2. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

3. **Add PostgreSQL addon**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Add Redis addon**
   ```bash
   heroku addons:create heroku-redis:mini
   ```

5. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key-here
   ```

6. **Deploy**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

7. **Scale worker dyno**
   ```bash
   heroku ps:scale worker=1
   ```

8. **Open your app**
   ```bash
   heroku open
   ```

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: Celery broker URL (usually same as REDIS_URL)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (usually same as REDIS_URL)
- `SECRET_KEY`: Secret key for application
- `UPLOAD_DIR`: Directory for temporary file uploads (default: uploads)
- `MAX_UPLOAD_SIZE`: Maximum upload size in bytes (default: 500MB)

## CSV Format

The CSV file should have the following columns:
- `sku` (required): Product SKU (case-insensitive, must be unique)
- `name` (required): Product name
- `description` (optional): Product description

Example CSV:
```csv
sku,name,description
ABC123,Product 1,Description 1
XYZ789,Product 2,Description 2
```

## API Endpoints

### Products
- `GET /api/products/` - List products with filtering and pagination
- `POST /api/products/` - Create a new product
- `GET /api/products/{id}` - Get a single product
- `PUT /api/products/{id}` - Update a product
- `DELETE /api/products/{id}` - Delete a product
- `DELETE /api/products/` - Delete all products

### Upload
- `POST /api/upload/` - Upload CSV file for processing

### Progress
- `GET /api/progress/{task_id}` - SSE endpoint for upload progress

### Webhooks
- `GET /api/webhooks/` - List all webhooks
- `POST /api/webhooks/` - Create a webhook
- `PUT /api/webhooks/{id}` - Update a webhook
- `DELETE /api/webhooks/{id}` - Delete a webhook
- `POST /api/webhooks/{id}/test` - Test a webhook

## Key Features Implementation

### Case-Insensitive SKU Handling
Products are matched by SKU using case-insensitive comparison. If a product with the same SKU (case-insensitive) exists, it will be updated instead of creating a duplicate.

### Asynchronous Processing
Large CSV files are processed asynchronously using Celery workers to avoid timeout issues (e.g., Heroku's 30-second limit). The processing happens in chunks of 1000 rows for optimal memory usage.

### Real-time Progress Updates
Server-Sent Events (SSE) are used to provide real-time progress updates to the frontend without polling.

### Webhook System
Webhooks are automatically triggered on product events. Failed webhook calls don't affect the main operation and are logged for debugging.

## Testing

1. **Test CSV Upload**
   - Create a CSV file with test products
   - Upload through the UI
   - Monitor progress in real-time
   - Verify products are imported correctly

2. **Test Product Management**
   - Create, update, and delete products
   - Test filtering and pagination
   - Test bulk delete

3. **Test Webhooks**
   - Create a webhook pointing to a test endpoint (e.g., webhook.site)
   - Perform product operations
   - Verify webhooks are triggered

## Notes

- The application automatically creates database tables on first run
- Uploaded CSV files are temporarily stored and cleaned up after processing
- Webhook failures are logged but don't interrupt the main operation
- All product operations trigger appropriate webhooks if configured

## License

This project is created for assessment purposes.

