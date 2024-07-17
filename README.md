# LinkedIn Group Post Automation

This Python script automates the process of posting to a specific LinkedIn group by leveraging the Playwright library for browser automation and a custom CAPTCHA solver for handling CAPTCHA challenges.

## Features

- Automated login to LinkedIn.
- Navigation to a specified LinkedIn group.
- Posting to the group (functionality to be implemented in further sections of the script).

## Prerequisites

Ensure you have the following installed:

- Python 3.6 or higher.
- Playwright for Python.
- Python-dotenv for loading environment variables.
- Pandas for data manipulation (if needed for managing posts).
- A custom CAPTCHA solver module (assumed to be part of the project).

Additionally, you need a `.env` file in the `CREDENTIALS` directory with your LinkedIn `EMAIL` and `PASSWORD`.

## Installation

1. Clone the repository or download the script.
2. Install the required dependencies:

   ```bash
   pip install playwright python-dotenv pandas
   playwright install

# Environment Variables Configuration

This document provides an overview of the environment variables required for the application to run properly. Ensure these variables are correctly set in your `.env` file located at the root of the project.

## Required Environment Variables

- `EMAIL`: This variable should hold the email address used for authentication or sending emails through the application. Ensure it is a valid email address format.

- `PASSWORD`: This variable is used for authentication purposes. It should be a strong, secure password that is kept confidential.

## Setting Up Your `.env` File

1. Locate the `.env` file at the root of your project. If it does not exist, create a new file named `.env`.

2. Open the `.env` file with a text editor of your choice.

3. Add the following lines to the file, replacing the placeholder values with your actual information:


