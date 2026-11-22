# Results: mnv3_large_int8_pte

Model: mnv3_large_int8.pte (ExecuTorch INT8, XNNPACK) through the Python runtime, temperature 0.687

| set | images | accuracy | macro F1 | crop known accuracy | crop known macro F1 | wrong crop |
|---|---|---|---|---|---|---|
| Lab test (PlantVillage) | 1135 | 0.9850 | 0.9860 | 0.9885 | 0.9894 | 0.0035 |
| Field test (field photos only) | 1020 | 0.9324 | 0.8928 | 0.9422 | 0.8989 | 0.0118 |

## Lab test (PlantVillage), per class

| class | precision | recall | F1 | images |
|---|---|---|---|---|
| potato_early_blight | 1.000 | 1.000 | 1.000 | 100 |
| potato_healthy | 1.000 | 1.000 | 1.000 | 15 |
| potato_late_blight | 1.000 | 0.960 | 0.980 | 100 |
| tomato_early_blight | 0.926 | 1.000 | 0.962 | 100 |
| tomato_healthy | 0.994 | 1.000 | 0.997 | 158 |
| tomato_late_blight | 0.973 | 0.963 | 0.968 | 190 |
| tomato_leaf_mold | 0.969 | 1.000 | 0.984 | 95 |
| tomato_septoria_leaf_spot | 1.000 | 0.977 | 0.989 | 177 |
| tomato_yellow_leaf_curl_virus | 1.000 | 0.990 | 0.995 | 200 |

![confusion test_lab](confusion_test_lab.png)

## Field test (field photos only), per class

| class | precision | recall | F1 | images |
|---|---|---|---|---|
| potato_early_blight | 0.982 | 0.942 | 0.961 | 172 |
| potato_healthy | 0.981 | 0.981 | 0.981 | 209 |
| potato_late_blight | 0.954 | 0.974 | 0.964 | 235 |
| tomato_early_blight | 0.842 | 0.753 | 0.795 | 85 |
| tomato_healthy | 0.852 | 0.767 | 0.807 | 30 |
| tomato_late_blight | 0.942 | 0.867 | 0.903 | 113 |
| tomato_leaf_miner | 0.897 | 1.000 | 0.945 | 104 |
| tomato_leaf_mold | 0.676 | 0.958 | 0.793 | 24 |
| tomato_septoria_leaf_spot | 0.833 | 0.926 | 0.877 | 27 |
| tomato_yellow_leaf_curl_virus | 0.947 | 0.857 | 0.900 | 21 |

![confusion test_field](confusion_test_field.png)
