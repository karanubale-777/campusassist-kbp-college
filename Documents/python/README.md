# CampusAssist – KBP College Vashi

CampusAssist is a Python-based college FAQ chatbot developed for **Karmaveer Bhaurao Patil College, Vashi**.

It is a goal-based college information assistant that helps students and visitors find information about courses, admissions, examinations, scholarships, library services, facilities, notices, fees, hostel information and contact details.

## Features

* Goal-Based FAQ chatbot
* CustomTkinter graphical user interface
* Login and user registration
* Admin account and admin statistics
* SQLite database for users and chat history
* Retrieves information from the official KBP College website
* Supports course-specific questions
* Provides information about:

  * Courses and programmes
  * Admission
  * Examinations
  * Scholarships
  * Library
  * Facilities
  * Notices
  * Fees
  * Hostel
  * Contact details
  * College information

## Technologies Used

* Python
* CustomTkinter
* Tkinter
* SQLite
* urllib
* Regular Expressions
* HTML data retrieval

## Installation

Make sure Python is installed on your computer.

Install the required package:

```bash
pip install -r requirements.txt
```

## Run the Application

Run:

```bash
python college_faq_chatbot.py
```

## Demo Admin Account

For demonstration purposes:

```text
Username: admin
Password: admin123
```

Change the default credentials before using the application in a real deployment.

## Database

The application uses SQLite to store:

* User accounts
* Password hashes and salts
* User roles
* Chat history
* Account creation information

The database is created automatically when the application runs.

## Official Information Source

CampusAssist uses the official KBP College Vashi website as its primary information source.

Official website:

https://www.kbpcollegevashi.edu.in/

## Project Structure

```text
CampusAssist/
│
├── college_faq_chatbot.py
├── README.md
├── requirements.txt
└── .gitignore
```

## College

**Karmaveer Bhaurao Patil College, Vashi**

Location: Vashi, Navi Mumbai, Maharashtra

## Purpose

The purpose of CampusAssist is to provide students with a simple desktop interface for accessing college-related information and navigating common college questions.

## Note

Information retrieved from the college website may change over time. CampusAssist is designed to retrieve current information from the official website when users ask questions.
