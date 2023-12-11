import face_recognition
import cv2
import numpy as np
import math
import os
from flask import session
import sys
from gridfs import GridFS
import pymongo
import io

def face_confidence(face_distance, face_match_threshold=0.4):
    range_val = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (range_val * 2.0)

    if face_distance > face_match_threshold:
        return str(round(linear_val * 100, 2)) + '%'
    else:
        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return str(round(value, 2)) + '%'

class FaceRecognition_member:
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    process_current_frame = True

    def __init__(self):
        self.encode_faces_from_mongodb()
    def encode_faces_from_mongodb(self):
        myclient = pymongo.MongoClient("mongodb+srv://team17:TqZI3KaT56q6xwYZ@team17.ufycbtt.mongodb.net/")
        mydb = myclient.face
        fs = GridFS(mydb, collection="faces")

        # 查询数据库中的图像集合（假设图像存储在名为 'faces' 的集合中）
        images = fs.find()

        for image_data in images:
            # 从 GridFS 获取图像数据
            grid_out = fs.get(image_data._id)
            image_binary = grid_out.read()

            # 将二进制数据转换为图像
            face_image = face_recognition.load_image_file(io.BytesIO(image_binary))

            # 进行人脸编码
            face_encoding = face_recognition.face_encodings(face_image)

            if len(face_encoding) > 0:
                face_encoding = face_encoding[0]

                # 存储人脸编码和名称
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(image_data.filename)  # 使用图像的文件名作为名称

        myclient.close()  # 关闭 MongoDB 连接

        print(self.known_face_names)

    def run_recognition(self, frame):
        frame = cv2.flip(frame, 1)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        self.face_locations = face_recognition.face_locations(rgb_small_frame)
        self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)

        self.face_names = []
        name = 'Unknown'
        for face_encoding in self.face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)

            confidence = 'Unknown'

            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index] and face_distances[best_match_index] <= 0.35:  # 設定閾值為0.75
                name = self.known_face_names[best_match_index]
                confidence = face_confidence(face_distances[best_match_index])



            self.face_names.append(f'{name}({confidence})')

        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), -1)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)



        return frame, name