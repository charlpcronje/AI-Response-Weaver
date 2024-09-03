# AI Response Weaver Technical Specification

## **1. Project Setup**

1.1 **Initialize Git Repository**  
- Create a new Git repository for version control.
- Set up a `.gitignore` file to exclude unnecessary files (e.g., `.env`, log files, etc.).

1.2 **Create Virtual Environment**  
- Set up a Python virtual environment using `venv` or `virtualenv`.
- Install necessary dependencies, including `gitpython` for Git integration and `watchdog` for file monitoring.

1.3 **Set Up Configuration Files**  
- Create a `.env` file to store the executable file name for VS Code (`code-server`).
- Create a `config.json` file to store file types, extensions, and comment syntax.

1.4 **Create Project Directory Structure**  
- Organize the project into directories:
  - `src/`: Contains the main application logic.
  - `config/`: Contains configuration files, including `config.json`.
  - `logs/`: Default folder for storing log files.
  - `tests/`: Contains unit tests.

---

## **2. JSON Configuration for File Types**

2.1 **Define JSON Structure for File Types**  
- Create a JSON file (`config.json`) that defines:
  - File types (e.g., Python, HTML).
  - Extensions (e.g., `.py`, `.html`).
  - Comment syntax for identifying file names.
  - Regular expressions for parsing file names and relative paths.

2.2 **Load JSON Configuration**  
- Write a Python function to load the JSON file and parse it into a dictionary for easy access during file creation.

---

## **3. Monitor and Parse File Changes**

3.1 **Monitor Specific File for Changes**  
- Implement a command-line argument to specify a file to monitor.
- Use the `watchdog` library to detect changes in the specified file.

3.2 **Parse File Content on Change**  
- Upon detecting a change, read the file content.
- Use regular expressions to extract code blocks from the file.
- For each code block, parse the first line to determine the file name and relative path.

---

## **4. File Creation and Directory Management**

4.1 **Create File Paths**  
- Check if the relative file path exists; if not, create the directory structure using `os.makedirs()`.

4.2 **Create or Update Files**  
- If the file doesn’t exist, create it and write the content.
- If the file exists, create a new Git branch, overwrite the file, and then trigger a merge process in VS Code.

4.3 **Git Integration for Merging**  
- Use `gitpython` to:
  - Create a new branch.
  - Overwrite the existing file with the new content.
  - Trigger a merge in VS Code using `subprocess.run()`.

---

## **5. Log File Management**

5.1 **Create Log Folder for Markdown Files**  
- Implement a command-line argument to specify a log folder.
- If no folder is provided, prompt the user for one.
- Ensure the log folder exists; if not, create it.

5.2 **Save Processed Responses as Markdown**  
- After parsing each response, save the content to a markdown file.
- Name the file with the current date and time (`YYYYMMDD_HHMMSS.md`).
- Store the file in the specified log folder.

---

## **6. Response Validation and Error Logging**

6.1 **Validate Response Structure**  
- Implement a validation step before processing each response.
- Check for correct formatting according to rules in `config.json`.
- If validation fails, log the error with details (timestamp, error description) to a separate error log file.

6.2 **Error Logging**  
- Create an `errors/` directory to store error logs.
- Log errors in a structured format, including the date, time, and type of error.

---

## **7. CLI and .weaver Configuration**

7.1 **Run the App with Arguments**  
- Implement a command-line interface (CLI) to run the app with arguments:
  - `weaver <file_to_monitor> <log_folder>`
  - Monitor the specified file and save logs to the provided folder.

7.2 **Create and Use .weaver Configuration Files**  
- When running the app, create a `.weaver` file in the current directory with the monitored file and log folder.
- If the app is run without arguments, check for a `.weaver` file in the current directory and use its configuration.
- If no `.weaver` file or arguments are provided, prompt the user for the file to monitor and the log folder, then save the configuration.

---

## **8. Application Deployment**

8.1 **Make the App Executable from Anywhere**  
- Add the app to the system’s PATH by creating a symlink or adding a shell script to `/usr/local/bin/` that points to the app’s main script.
- Ensure the app can be run using `weaver` from any directory.

8.2 **Create a Setup Script**  
- Write a setup script (`setup.sh`) to install dependencies, set up the virtual environment, and configure the environment for first-time use.

---

## **9. Testing and Validation**

9.1 **Write Unit Tests**  
- Create unit tests for each functionality (e.g., file monitoring, parsing, file creation, Git operations).
- Ensure 100% code coverage for critical functions.

9.2 **Run Tests**  
- Automate testing with a continuous integration tool like GitHub Actions or Jenkins.
- Verify that all tests pass before deployment.