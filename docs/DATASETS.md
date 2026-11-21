# Datasets

We cover two crops, tomato and potato, with 10 classes in total. Lab photos alone train a model that falls apart in a real field, so most of the effort here goes into collecting field photos for every class and keeping a test set that has only field photos in it.

None of the images live in this repo. `detection/data/download.py` fetches everything from the original sources, and `detection/data/build_dataset.py` turns it into train, validation and test splits.

## Sources

| # | Dataset | Type of photos | Where it comes from | Licence | Link |
|---|---|---|---|---|---|
| 1 | PlantVillage | Lab, single leaf on a plain background | Penn State PlantVillage project (Hughes and Salathe, 2015) | No licence file in the repo. Cite the paper. | https://github.com/spMohanty/PlantVillage-Dataset |
| 2 | PlantDoc | Field and web photos, cluttered backgrounds | IIT Gandhinagar (Singh et al., 2020) | CC BY 4.0 | https://github.com/pratikkayal/PlantDoc-Dataset |
| 3 | PlantSeg | Field and web photos, with lesion masks | University of Queensland and partners (Wei et al., 2024) | CC BY-NC 4.0 | https://zenodo.org/records/17719108 |
| 4 | Tomato-Village | Field photos from Jodhpur and Jaipur, Rajasthan | Gehlot et al., Multimedia Systems, 2023 | No licence file in the repo. Cite the paper. | https://github.com/mamta-joshi-gehlot/Tomato-Village |
| 5 | Potato Leaf Disease in Uncontrolled Environment | Field photos from farms in Central Java, Indonesia | Shabrina et al., Data in Brief, 2024 | CC BY 4.0 | https://data.mendeley.com/datasets/ptz377bwb8/1 |
| 6 | Potato Leaf (Healthy and Late Blight) | Field photos from Holeta, Ethiopia | Mendeley Data | CC BY 4.0 | https://data.mendeley.com/datasets/v4w72bsts5/2 |

PlantSeg is non-commercial only. That is fine for the challenge, but it has to be dropped if this ever becomes a product. Tomato-Village and PlantVillage have no licence file, so we only download them in our scripts and never re-host the images.

## What we take from each source

Numbers are image counts as published by each source, before we remove duplicates. The final counts after cleaning are written to `docs/data_counts.md` when the build script runs.

| Our class | PlantVillage (lab) | PlantDoc (field) | PlantSeg (field) | Tomato-Village (field) | Potato Indonesia (field) | Potato Ethiopia (field) | Field total |
|---|---|---|---|---|---|---|---|
| tomato_healthy | 1,591 (Tomato___healthy) | 63 (Tomato leaf) | | 216 (Healthy) | | | 279 |
| tomato_early_blight | 1,000 (Tomato___Early_blight) | 88 (Tomato Early blight leaf) | 187 (tomato_early_blight) | 496 (Early_blight) | | | 771 |
| tomato_late_blight | 1,909 (Tomato___Late_blight) | 111 (Tomato leaf late blight) | 163 (tomato_late_blight) | 904 (Late_blight) | | | 1,178 |
| tomato_leaf_mold | 952 (Tomato___Leaf_Mold) | 91 (Tomato mold leaf) | 156 (tomato_leaf_mold) | | | | 247 |
| tomato_septoria_leaf_spot | 1,771 (Tomato___Septoria_leaf_spot) | 151 (Tomato Septoria leaf spot) | 130 (tomato_septoria_leaf_spot) | | | | 281 |
| tomato_yellow_leaf_curl_virus | 5,357 (Tomato___Tomato_Yellow_Leaf_Curl_Virus) | 76 (Tomato leaf yellow virus) | 93 (tomato_yellow_leaf_curl_virus) | | | | 169 |
| tomato_leaf_miner (pest) | | | | 1,024 (Leaf Miner) | | | 1,024 |
| potato_healthy | 152 (Potato___healthy) | | | | 201 (Healthy) | 363 (Healthy) | 564 |
| potato_early_blight | 1,000 (Potato___Early_blight) | 117 (Potato leaf early blight) | 126 (potato_early_blight) | | | | 243 |
| potato_late_blight | 1,000 (Potato___Late_blight) | 105 (Potato leaf late blight) | 117 (potato_late_blight) | | 347 (Phytophthora) | 63 (Late Blight) | 632 |

PlantSeg counts include both its own field photos and the images its authors collected from web search (file names ending in `_google`).

### What we leave out, and why

- **Indonesia potato "Fungi" (748 images).** It mixes several fungal diseases under one label. Early blight is one of them, but nothing marks which photos are which, so putting them under early blight would add wrong labels.
- **Indonesia potato Bacteria, Virus, Nematode and Pest.** These are outside our class list.
- **Tomato-Village nutrient deficiency and spotted wilt classes.** These are outside our class list for now. Spotted wilt is a good candidate for the next round.
- **Other PlantVillage tomato classes** (bacterial spot, target spot, mosaic virus, spider mites). Kept out to stay close to the 4 to 6 classes per crop the mentors suggested. Leaf curl virus and leaf miner were chosen instead because they are among the most common tomato problems in Indian fields.
- **Kaggle re-uploads such as "New Plant Diseases Dataset".** Most are augmented copies of PlantVillage, which would leak near-identical images into the test set.

## How we keep the classes balanced

1. **Remove duplicates first.** Every image gets a perceptual hash. Images within a small hash distance of each other count as one, across all sources. PlantDoc and the web half of PlantSeg were both scraped from search engines, so some overlap is expected.
2. **Field photos go in first.** For each class we use every field photo in the training split, up to 700.
3. **Lab photos fill the gap.** PlantVillage photos are added until the class reaches 1,000 training images. Leaf curl virus has 5,357 lab photos, so this cap is what stops it from swamping everything else.
4. **Sampling evens out the rest.** Two classes cannot reach 1,000: potato_healthy (about 600 total) and tomato_leaf_miner (field only). Training uses a weighted sampler so each class is drawn about equally often per epoch, with field photos weighted higher than lab photos.
5. **The augmentation is built for field conditions.** Random crops, rotation, colour and brightness changes, blur and partial occlusion, so lab photos look a bit more like phone photos taken outdoors.

## Splits

- **Test (field only, never trained on):** the PlantDoc test split, the PlantSeg test split, the Tomato-Village test split, and a 20 percent stratified hold-out from the two potato field datasets.
- **Validation:** the PlantSeg and Tomato-Village validation splits, plus 10 percent of everything else.
- **Train:** the rest, after the balancing above.

If a near-duplicate of a test image shows up in train, the train copy is removed.

We report two accuracy numbers: one on the PlantVillage test images, which is always high and mostly shows the model learned something, and one on the field-only test set, which is the number that matters.

## Citations

- Hughes, D. P. and Salathe, M. An open access repository of images on plant health to enable the development of mobile disease diagnostics. arXiv:1511.08060, 2015.
- Singh, D. et al. PlantDoc: A Dataset for Visual Plant Disease Detection. CoDS-COMAD 2020.
- Wei, T. et al. PlantSeg: A Large-Scale In-the-wild Dataset for Plant Disease Segmentation. arXiv:2409.04038, 2024.
- Gehlot, M., Saxena, R. K. and Gandhi, G. C. Tomato-Village: a dataset for end-to-end tomato disease detection in a real-world environment. Multimedia Systems, 2023.
- Shabrina, N. H. et al. A novel dataset of potato leaf disease in uncontrolled environment. Data in Brief 52, 109955, 2024.
- Potato Leaf (Healthy and Late Blight), Mendeley Data, doi:10.17632/v4w72bsts5.2.
