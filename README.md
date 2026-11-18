Introduction
You’ll build a web app with a simple UI where a user can sign up for an account. Once logged in, the user is presented with a simple form to add medicine name, dosages, and frequency. After adding those details, the user can view, edit, or delete this information. The rough estimate for this project is 20 hours.

Requirements
Signup page and API: User can sign up for an account.
Login page and API: After signup, the user can log in to their account.
Account page: On this page, the user can add and view medicines.
Input for the new data can be taken via an HTML form which has three fields:
Medicine Name - String
Dosage - Quantity (Integer) with units (String) or a freeform text field (String)
Frequency - Quantity (Integer) with units (String) or freeform text field (String)
The user can see their data in the form of a list (tracked medicines, dosages, and frequency). They can also update and delete existing data. Update can be done via a similar form as adding new data (with field values already populated with existing data).
For an extra challenge:

Build/use a cron job or service to send email or text reminders to the user to take the medicine at the right time.
Suggested Implementation
If you want to use Python, below is the recommended stack and libraries:

Flask, Django, FastAPI for back-end APIs
Django templates along with CSS frameworks (e.g. Bootstrap) for UI
PostgreSQL or MySQL for the database
Heroku for hosting the web app
Scheduled jobs and logging libraries in Heroku
References
Flask Tutorial
Python on Heroku
Bootstrap