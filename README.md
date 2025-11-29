# MailHarvester

A Streamlit-based application to browse Gmail, compose emails, and generate AI-assisted replies using **Google Gemini**.

## 🌟 Overview

This tool allows you to:

- 📬 Browse your Gmail inbox  
- 🔍 Search emails with custom queries  
- 📝 View email snippets, plain text, or HTML content  
- ✉️ Compose new emails  
- 🤖 Generate AI-assisted replies using Google Gemini  
- ✅ Mark emails as read after replying  

Built with **Python**, **Streamlit**, and **Google APIs**.


## ⚡ Features

- 🔐 Connect securely to Gmail via OAuth2  
- 🔎 Search and fetch emails based on queries (e.g., `is:unread`, `newer_than:7d`)  
- 🗂 Read emails in plain text or HTML view  
- 🤖 Automatically generate professional replies using Google Gemini AI  
- ✉️ Compose and send new emails directly from the app  


## 🛠 Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/Dhivakar2005/MailHarvester.git
    cd MailHarvester
    ```

2. **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    # Activate (Windows)
    venv\Scripts\activate
    # Activate (Linux/Mac)
    source venv/bin/activate
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Create a `.env` file and add your Gemini API key:**

    ```text
    GEMINI_API_KEY=your_api_key_here
    ```

5. **Upload your `credentials.json` from Google Cloud** in the Streamlit sidebar when running the app.


## 🚀 Usage

Run the app:

  ```bash
    streamlit run app.py
```
- Use the sidebar to upload credentials.json and manage login
- Select either 📥 Search Emails or ✉️ Compose New Email tab
- For each fetched email, generate a draft reply with Gemini AI and send directly from the app
  
This is properly formatted with the code block closed and clean bullet points.  

I can also combine this with your **Installation section and full README** into a complete single `README.md` ready to paste into your project. Do you want me to do that?


## 🔑 Environment Variables

GEMINI_API_KEY – required to use Google Gemini AI for generating replies

## 🤝 Contributing

Contributions are welcome! Submit issues or pull requests for bug fixes and feature improvements.

## 📄 License

MIT License. See LICENSE for details.
