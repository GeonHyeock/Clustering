import cv2
import streamlit as st
import numpy as np
import pandas as pd
import os
import zipfile
import io
from stqdm import stqdm
from util import draw_bbox_array, Infer, make_csv, xywh2xyxy


def main():
    st.title("Clustering")

    with st.sidebar:
        sic = st.checkbox("Show Inference confidence")
        conf_thres = st.slider("conf_thres", 0.0, 1.0, 0.4, 0.01)
        iou_thres = st.slider("iou_thres", 0.0, 1.0, 0.45, 0.01)

    tab1, tab2, tab3 = st.tabs(["Inference", "Batch Inference", "Train model result"])

    with tab1:
        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image_bytes = uploaded_file.getvalue()
            image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), flags=1)
            col1, col2 = st.columns(2)
            with col1:
                st.write("원본")
                st.image(image)

            draw_img_array = np.expand_dims(np.swapaxes(image, 0, 2), 0).astype(np.float32) / 255
            result = Infer(image, conf_thres, iou_thres)[:-1]

            with col2:
                st.write("결과")
                draw_img_array, det = draw_bbox_array(result, (640, 640), image, sic)
                st.image(draw_img_array)

                csv = make_csv(det)
                st.download_button(
                    label="Download result CSV",
                    data=pd.DataFrame(csv).reset_index().to_csv(index=False).encode("utf-8"),
                    file_name=f"{'.'.join(uploaded_file.name.split('.')[:-1])}_result.csv",
                )

    with tab2:
        with st.form("my-form", clear_on_submit=True):
            uploaded_zip = st.file_uploader("Choose an image ZIP", type=["zip"])
            submitted = st.form_submit_button("파일 분석")
            if submitted and uploaded_zip is not None:
                zip_name = uploaded_zip.name[:-4]
                with zipfile.ZipFile(uploaded_zip, "r") as z:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "x") as csv_zip:
                        files = [f for f in z.namelist() if f.split(".")[-1] in ["jpg", "jpeg", "png"]]
                        for file in stqdm(files):
                            image = np.frombuffer(z.read(file), np.uint8)
                            image = cv2.imdecode(image, flags=1)
                            result = Infer(image, conf_thres, iou_thres)[:-1]
                            det = draw_bbox_array(result, (640, 640), image, sic, only_det=True)
                            csv = make_csv(det)
                            csv_name = ".".join(file.replace(zip_name, zip_name + "_result").split(".")[:-1] + ["csv"])
                            csv_zip.writestr(csv_name, pd.DataFrame(csv).to_csv(index=False))
        if submitted and uploaded_zip is not None:
            st.download_button(
                label="Download result zip",
                data=buf.getvalue(),
                file_name=zip_name + "_result.zip",
                mime="application/zip",
            )

    with tab3:
        data_type = st.radio(
            "Set selectbox data_type",
            options=["train", "valid", "test"],
        )
        image_path = f"./data/{data_type}/images"
        label_path = f"./data/{data_type}/labels"

        img_path = st.selectbox(
            "image를 선택해주세요.",
            os.listdir(image_path),
        )
        agree = st.checkbox("추론 결과를 원한다면 체크해주세요.")
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
            if agree:
                result = Infer(img, conf_thres, iou_thres)[:-1]
                draw_img_array, det = draw_bbox_array(result, (640, 640), img, sic)
                st.image(draw_img_array)


if __name__ == "__main__":
    main()
