# HMS (Hostel Management System)

This is a Student Management System (HMS) project built with Python. It provides authentication, chat, complaints, dashboard, and hostel management features.

## Prerequisites

- Python 3.10 or higher
- [pip](https://pip.pypa.io/en/stable/)

## Setup Instructions

1. **Clone the repository**

   ```bash
   cd hms
   ```

2. **Verify Python Installation**
    ```bash
    python3 --version
    ```

2. **(Optional) Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**

   ```bash
   python main.py
   ```

5. **Access the application**

   Open your browser and go to `http://127.0.0.1:8000` (or the port specified in your app).

## Project Structure

- `main.py` - Entry point of the application
- `src/` - Source code modules
- `templates/` - HTML templates
- `requirements.txt` - Python dependencies

## Notes

- Make sure to configure any environment variables or database settings as required in `src/common/config.py`.
- For development, you may want to enable debug mode in your application settings.

## License

This project is for educational purposes.
