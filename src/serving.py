import argparse
import requests
import mlflow
import cv2
import streamlit as st
import numpy as np
import pandas as pd
import os
from infer import draw_bbox_array, Infer, make_csv, xywh2xyxy


@st.cache_data()
def load_model(logged_model="runs:/096a362268c64363b896555db566d5d5/model"):
    loaded_model = mlflow.pyfunc.load_model(logged_model)
    return loaded_model


def infer(image):
    res = requests.post(
        url=args.uri,
        json={"inputs": image},
        headers={"Content-Type": "application/json"},
    )
    if res.status_code == 200:
        result = res.json()
        return result["predictions"]
    else:
        print("Request failed with status code:", res.status_code)


def main(args):
    st.title("Clustering")

    with st.sidebar:
        sic = st.checkbox("Show Inference confidence")

    if "model" not in st.session_state:
        st.session_state.model = load_model()

    tab1, tab2 = st.tabs(["Inference", "Train model result"])

    with tab1:
        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_bytes = uploaded_file.getvalue()
            image = cv2.imdecode(np.fromstring(image_bytes, np.uint8), flags=1)
            col1, col2 = st.columns(2)
            with col1:
                st.write("원본")
                st.image(image)

            # demo

            draw_img_array = (
                np.expand_dims(np.swapaxes(image, 0, 2), 0).astype(np.float32) / 255
            )
            result = Infer(st.session_state.model, image)[:-1]

            with col2:
                st.write("결과")
                draw_img_array, det = draw_bbox_array(result, (640, 640), image, sic)
                st.image(draw_img_array)

                csv = make_csv(det)
                st.download_button(
                    label="Download result CSV",
                    data=pd.DataFrame(csv)
                    .reset_index()
                    .to_csv(index=False)
                    .encode("utf-8"),
                    file_name=f"{'.'.join(uploaded_file.name.split('.')[:-1])}_result.csv",
                )

    with tab2:
        data_type = st.radio(
            "Set selectbox data_type",
            options=["train", "valid", "test"],
        )
        image_path = f"/home/user/clustering/data/{data_type}/images"
        label_path = f"/home/user/clustering/data/{data_type}/labels"
        img_path = st.selectbox(
            "image를 선택해주세요.",
            os.listdir(image_path),
        )

        tab2_col1, tab2_col2, tab2_col3 = st.columns(3)
        with tab2_col1:
            st.write("원본")
            img = cv2.imread(os.path.join(image_path, img_path))
            st.image(img)

        with tab2_col2:
            st.write("원본 bbox")
            label = img_path.replace("jpg", "txt")
            df = pd.read_table(
                os.path.join(label_path, label),
                sep=" ",
                header=None,
                index_col=0,
            )
            det = np.append(xywh2xyxy(df.values), [[1, 0]] * len(df.values), axis=1)
            draw_img_array, det = draw_bbox_array(det, (1, 1), img, sic)
            st.image(draw_img_array)

        with tab2_col3:
            st.write("추론 bbox")
            result = Infer(st.session_state.model, img)[:-1]
            draw_img_array, det = draw_bbox_array(result, (640, 640), img, sic)
            st.image(draw_img_array)

        st.write("metric_chart")
        st.image("data/스크린샷 2023-10-21 오전 2.31.35.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--uri",
        default="http://127.0.0.1/invocations",
        help="serving된 모델 uri",
    )
    args = parser.parse_args()

    main(args)