# SmartAttend – Face Recognition Attendance Management System

A webcam-based student attendance management system built with Python, Flask, SQLite, and OpenCV face recognition. SmartAttend allows administrators to manage student records, capture live face photos, recognize registered students through a webcam, and generate attendance reports.

## 🚀 Features

- **Face Recognition:** Identifies registered students using webcam input.
- **Live Photo Capture:** Captures student photos directly from the webcam during registration.
- **Student Management:** Add, edit, search, and delete student records.
- **Automated Attendance:** Records attendance with date and time when a registered student is recognized.
- **Admin Dashboard:** Displays student and attendance statistics.
- **Attendance Records:** View attendance history and manage records.
- **CSV Reports:** Export attendance reports for record-keeping.
- **SQLite Database:** Stores student information, face embeddings, and attendance records.
- **Web-Based Interface:** Provides a user-friendly interface for administrators and attendance monitoring.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database management |
| OpenCV | Computer vision and face recognition |
| YuNet | Face detection |
| SFace | Face feature extraction and recognition |
| HTML5 | Web page structure |
| CSS3 | Styling and responsive layout |
| JavaScript | Frontend interactions |
| Git and GitHub | Version control |

## 📂 Project Structure

```text
Attendanceproj/
├── app.py
├── Attendanceproj.py
├── database.py
├── requirements.txt
├── view_database.py
├── models/
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── students.html
│   ├── add_student.html
│   ├── edit_student.html
│   ├── student_form.html
│   ├── attendance.html
│   ├── camera.html
│   ├── kiosk.html
│   ├── login.html
│   └── 404.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── css/js/
│       └── main.js
├── uploads/
├── known_faces/
└── .gitignore
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/akshay-java-dev/Attendanceproj.git
cd Attendanceproj
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Prepare the face recognition models

Ensure the following model files are available inside the `models/` directory:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`

Check the applicable model licenses before downloading or redistributing them.

### 5. Run the application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## 👨‍💻 How It Works

1. The administrator signs in to the SmartAttend portal.
2. Student details are entered and a face photo is uploaded or captured using the webcam.
3. The system detects the face and extracts its features for recognition.
4. The registered student appears in the student management section.
5. At the attendance kiosk, the webcam scans faces and compares them with registered face data.
6. When a registered student is recognized, attendance is recorded with the date and time.
7. Administrators can view attendance records and export reports as CSV files.

## 🔐 Security and Privacy

- Keep student photos, face embeddings, and database files private.
- Do not commit passwords, secret keys, or confidential student information to GitHub.
- Use environment variables for sensitive configuration.
- Restrict access to the administrator portal.
- Obtain appropriate consent before collecting or processing students' facial data.

## 🎯 Project Objective

The objective of SmartAttend is to simplify student attendance management by reducing manual record-keeping and using webcam-based face recognition to identify registered students and record attendance efficiently.

## 🔮 Future Enhancements

- Improved face recognition accuracy under different lighting conditions.
- Attendance analytics and visual reports.
- Improved student search and filtering.
- Role-based access control.
- Deployment to a secure web server.

## 👤 Author

**Akshay Kumbhar**

GitHub: [@akshay-java-dev](https://github.com/akshay-java-dev)

## 📄 License

Choose and add an appropriate open-source license before permitting others to reuse or redistribute this project.
