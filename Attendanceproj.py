import cv2
import face_recognition
import numpy as np
import pandas as pd
from datetime import datetime
import os

# =========================================================
# 1. LOAD KNOWN FACES
# =========================================================

known_face_encodings = []
known_face_names = []

# Get project folder location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# known_faces folder
path = os.path.join(BASE_DIR, "known_faces")

# Check folder
if not os.path.exists(path):
    os.makedirs(path)
    print("Created 'known_faces' folder.")
    print("Please put your photo inside the known_faces folder.")
    exit()

# Allowed image files
image_extensions = (".jpg", ".jpeg", ".png")

for file in os.listdir(path):

    if not file.lower().endswith(image_extensions):
        continue

    image_path = os.path.join(path, file)

    print("Loading:", file)

    img = face_recognition.load_image_file(image_path)

    encodings = face_recognition.face_encodings(img)

    if len(encodings) == 0:
        print("WARNING: No face found in:", file)
        continue

    if len(encodings) > 1:
        print("WARNING: Multiple faces found in:", file)
        print("Use a photo containing only one person.")
        continue

    encoding = encodings[0]

    known_face_encodings.append(encoding)

    # Remove extension from filename
    name = os.path.splitext(file)[0]

    known_face_names.append(name)

print("Loaded known faces:", known_face_names)

# Check whether faces were loaded
if len(known_face_encodings) == 0:
    print()
    print("ERROR: No valid face found.")
    print("Put a clear face photo inside:")
    print(path)
    exit()


# =========================================================
# 2. ATTENDANCE FUNCTION
# =========================================================

def mark_attendance(name):

    file_name = os.path.join(BASE_DIR, "attendance.csv")

    # Create CSV if it doesn't exist
    if not os.path.exists(file_name):

        with open(file_name, "w") as f:
            f.write("Name,Time\n")

    # Read existing attendance
    with open(file_name, "r+") as f:

        data = f.readlines()

        names = [line.split(",")[0] for line in data]

        # Mark attendance only once
        if name not in names:

            now = datetime.now()

            time_string = now.strftime("%H:%M:%S")

            f.write(f"{name},{time_string}\n")

            print(f"Attendance marked for {name}")

            # =========================================================
            # ADD ATTENDANCE MANUALLY
            # =========================================================

            def add_attendance(name):
                file_name = os.path.join(BASE_DIR, "attendance.csv")

                now = datetime.now()
                time_string = now.strftime("%H:%M:%S")

                if not os.path.exists(file_name):
                    with open(file_name, "w") as f:
                        f.write("Name,Time\n")

                with open(file_name, "r") as f:
                    data = f.readlines()

                # Check if already present
                names = [line.split(",")[0].strip() for line in data[1:]]

                if name not in names:
                    with open(file_name, "a") as f:
                        f.write(f"{name},{time_string}\n")

                    print(f"Attendance added for {name}")
                else:
                    print(f"{name} is already present.")

            # =========================================================
            # DELETE ATTENDANCE
            # =========================================================

            def delete_attendance(name):
                file_name = os.path.join(BASE_DIR, "attendance.csv")

                if not os.path.exists(file_name):
                    print("Attendance file does not exist.")
                    return

                with open(file_name, "r") as f:
                    lines = f.readlines()

                header = lines[0]

                new_lines = [
                    line for line in lines[1:]
                    if line.split(",")[0].strip().upper() != name.upper()
                ]

                if len(new_lines) == len(lines) - 1:
                    print(f"No attendance found for {name}")
                    return

                with open(file_name, "w") as f:
                    f.write(header)
                    f.writelines(new_lines)

                print(f"Attendance deleted for {name}")

                # =========================================================
                # ATTENDANCE MANAGEMENT MENU
                # =========================================================

                while True:

                    print("\n==============================")
                    print("   ATTENDANCE MANAGEMENT")
                    print("==============================")
                    print("1. Add Attendance")
                    print("2. Delete Attendance")
                    print("3. Start Face Recognition")
                    print("4. Exit")
                    print("==============================")

                    choice = input("Enter your choice: ")

                    if choice == "1":

                        name = input("Enter name: ").strip()

                        if name:
                            add_attendance(name)

                    elif choice == "2":

                        name = input("Enter name to delete: ").strip()

                        if name:
                            delete_attendance(name)

                    elif choice == "3":

                        break

                    elif choice == "4":

                        exit()

                    else:

                        print("Invalid choice.")


# =========================================================
# 3. START WEBCAM
# =========================================================

video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():

    print("ERROR: Cannot open webcam.")

    exit()


print()
print("===================================")
print(" Attendance System Started")
print(" Press Q to Exit")
print("===================================")
print()


# =========================================================
# 4. FACE RECOGNITION
# =========================================================

while True:

    ret, frame = video_capture.read()

    if not ret:

        print("ERROR: Cannot read webcam.")
        break

    # Resize image for faster processing
    small_frame = cv2.resize(
        frame,
        (0, 0),
        fx=0.25,
        fy=0.25
    )

    # OpenCV uses BGR
    # face_recognition uses RGB
    rgb_small_frame = cv2.cvtColor(
        small_frame,
        cv2.COLOR_BGR2RGB
    )

    # Detect faces
    face_locations = face_recognition.face_locations(
        rgb_small_frame
    )

    # Generate face encodings
    face_encodings = face_recognition.face_encodings(
        rgb_small_frame,
        face_locations
    )


    # =====================================================
    # 5. CHECK EACH FACE
    # =====================================================

    for face_encoding, face_location in zip(
        face_encodings,
        face_locations
    ):

        # Compare with known faces
        matches = face_recognition.compare_faces(
            known_face_encodings,
            face_encoding,
            tolerance=0.5
        )

        face_distances = face_recognition.face_distance(
            known_face_encodings,
            face_encoding
        )

        # Find closest face
        best_match_index = np.argmin(face_distances)


        # =================================================
        # KNOWN PERSON
        # =================================================

        if matches[best_match_index]:

            name = known_face_names[
                best_match_index
            ].upper()

            mark_attendance(name)

        else:

            name = "UNKNOWN"


        # =================================================
        # 6. DRAW RECTANGLE
        # =================================================

        top, right, bottom, left = face_location

        # Because frame was resized to 25%
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4


        if name != "UNKNOWN":

            rectangle_color = (0, 255, 0)

        else:

            rectangle_color = (0, 0, 255)


        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            rectangle_color,
            2
        )


        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            rectangle_color,
            2
        )


    # =====================================================
    # 7. SHOW CAMERA
    # =====================================================

    cv2.imshow(
        "Attendance System",
        frame
    )


    # Press Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# =========================================================
# 8. CLOSE CAMERA
# =========================================================

video_capture.release()

cv2.destroyAllWindows()