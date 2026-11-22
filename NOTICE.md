# Notice

**Built with Llama**

The project code in this repository is under the MIT License (see `LICENSE`). The model, the datasets and the knowledge base sources below are not ours and keep their own licences.

## Llama 3.2

The advisory stage runs Llama 3.2 1B Instruct (the SpinQuant INT4 ExecuTorch build from the executorch-community page on Hugging Face). Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved. The full licence text is in `LICENSES/LLAMA_3.2_LICENSE.txt`. Use of the model must also follow the Llama 3.2 Acceptable Use Policy (https://www.llama.com/llama3_2/use-policy). We do not put the model file in this repository; it is downloaded separately.

## Datasets

The detection model is trained on these datasets. We only download them in our scripts and do not re-host the images. Details are in `docs/DATASETS.md` on `main`.

| Dataset | Licence | Credit |
|---|---|---|
| PlantVillage | CC BY-SA 3.0 as given by the PlantVillage project. The GitHub copy we download from has no licence file, so we also cite the paper. | Hughes, D. P. and Salathe, M. An open access repository of images on plant health to enable the development of mobile disease diagnostics. arXiv:1511.08060, 2015. https://github.com/spMohanty/PlantVillage-Dataset |
| PlantDoc | CC BY 4.0 | Singh, D. et al. PlantDoc: A Dataset for Visual Plant Disease Detection. CoDS-COMAD 2020. https://github.com/pratikkayal/PlantDoc-Dataset |
| PlantSeg | CC BY-NC 4.0 (non-commercial only) | Wei, T. et al. PlantSeg: A Large-Scale In-the-wild Dataset for Plant Disease Segmentation. arXiv:2409.04038, 2024. https://zenodo.org/records/17719108 |
| Tomato-Village | No licence file in the repository. Cite the paper. | Gehlot, M., Saxena, R. K. and Gandhi, G. C. Tomato-Village: a dataset for end-to-end tomato disease detection in a real-world environment. Multimedia Systems, 2023. https://github.com/mamta-joshi-gehlot/Tomato-Village |
| Potato Leaf Disease in Uncontrolled Environment | CC BY 4.0 | Shabrina, N. H. et al. A novel dataset of potato leaf disease in uncontrolled environment. Data in Brief 52, 109955, 2024. https://data.mendeley.com/datasets/ptz377bwb8/1 |
| Potato Leaf (Healthy and Late Blight) | CC BY 4.0 | Mendeley Data. https://data.mendeley.com/datasets/v4w72bsts5/2 |
| Potato Disease Leaf Dataset (PLD) | ODbL 1.0 (database), DbCL 1.0 (contents) | Rashid, J. et al. Multi-Level Deep Learning Model for Potato Leaf Disease Recognition. Electronics 10(17), 2064, 2021. https://www.kaggle.com/datasets/rizwan123456789/potato-disease-leaf-datasetpld |

PlantSeg is non-commercial only. That is fine for the challenge, but it has to be dropped if this ever becomes a product.

## Knowledge base sources

The facts, chemicals and doses in `advisory/kb/kb.json` were read from these public sources and rewritten in our own words. The full list, with what we took from each page, is in `advisory/kb/SOURCES.md`.

- NIPHM and Directorate of PPQS (Ministry of Agriculture and Farmers Welfare), AESA based IPM packages for Tomato and Potato. https://niphm.gov.in/IPMPackages/Tomato.pdf and https://niphm.gov.in/IPMPackages/Potato.pdf
- TNAU Agritech Portal, crop protection pages for tomato and potato diseases and pests. https://agritech.tnau.ac.in
- Cornell Vegetable Program, Tomato leaf mold. https://vegetables.cornell.edu/crops/tomatoes/tomato-leaf-mold
- Royal Horticultural Society, Tomato leaf mould. https://www.rhs.org.uk/disease/tomato-leaf-mould
