# Knowledge base sources

Every fact, chemical name and dose in `kb.json` was read from one of the sources below on 21 Nov 2026. The key in brackets is the id used in `kb.json`.

## Sources we used

| Key | Source | What we took from it |
|---|---|---|
| `niphm_tomato` | NIPHM and Directorate of PPQS (Ministry of Agriculture and Farmers Welfare), "AESA based IPM package: Tomato". https://niphm.gov.in/IPMPackages/Tomato.pdf | Cultural, biological and chemical steps for early blight, late blight, Septoria leaf spot, leaf curl (whitefly) and serpentine leaf miner. All tomato spray doses in the KB. Waiting periods (table XIV, page 85 to 88): imidacloprid 3 days, thiamethoxam 5 days, captan 6 days, mancozeb 10 days. Pesticide safety precautions (section XV). |
| `niphm_potato` | NIPHM and Directorate of PPQS, "AESA based IPM package: Potato". https://niphm.gov.in/IPMPackages/Potato.pdf | Early and late blight steps and doses (page 29 to 30 of the PDF), resistant Kufri varieties, waiting periods (table XIV, PDF page 64 to 67): mancozeb 10, chlorothalonil 10, dimethomorph 10, copper oxychloride 6 days. |
| `tnau_tomato_early_blight` | TNAU Agritech Portal, Tomato early blight. https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html | Symptoms, favourable weather (24 to 29 C), debris removal, crop rotation, Trichoderma asperellum seed treatment 4 g per kg. |
| `tnau_tomato_septoria` | TNAU Agritech Portal, Septoria leaf spot. https://agritech.tnau.ac.in/crop_protection/tomato_diseases_4.html | Symptoms, spread, removing affected parts, Trichoderma seed treatment. |
| `tnau_tomato_leaf_curl` | TNAU Agritech Portal, Tomato leaf curl. https://agritech.tnau.ac.in/crop_protection/tomato_diseases_6.html | Symptoms, whitefly vector, protected nursery, barrier crops, weed host Abutilon indicum. |
| `tnau_tomato_late_blight` | TNAU Agritech Portal, Tomato late blight. https://agritech.tnau.ac.in/crop_protection/tomato_diseases_8.html | Symptoms, weather, drainage, rotation, Trichoderma soil application 1 kg per acre. |
| `tnau_tomato_leaf_miner` | TNAU Agritech Portal, Serpentine leaf miner. https://agritech.tnau.ac.in/crop_protection/tomato/tomato_2.html | Damage, pest stages, removing mined leaves, NSKE 5%, cyantraniliprole 10.26 OD at 1.8 ml per litre. |
| `tnau_potato_late_blight` | TNAU Agritech Portal, Late blight of potato. https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg_potato_1.html | Symptoms on leaves, stems and tubers, weather, protective mancozeb spray, resistant varieties, haulm destruction, harvest care. |
| `tnau_potato_early_blight` | TNAU Agritech Portal, Early blight of potato. https://agritech.tnau.ac.in/crop_protection/crop_prot_crop%20diseases_veg_potato_2.html | Symptoms, weather, disease-free seed tubers, debris removal, early sprays every 15 to 20 days, Kufri Sindhuri. |
| `cornell_leaf_mold` | Cornell Vegetable Program, Tomato leaf mold. https://vegetables.cornell.edu/crops/tomatoes/tomato-leaf-mold | Cause, spread (humidity above 85%), symptoms, removing diseased plants, cleaning tools, clean seed, rotation. |
| `rhs_leaf_mould` | Royal Horticultural Society, Tomato leaf mould. https://www.rhs.org.uk/disease/tomato-leaf-mould | Yellow patches on top, mould underneath, ventilation, not wetting leaves, trimming lower leaves. |

## Choices and gaps

- **Where sources disagree we used the NIPHM package for doses.** For example TNAU gives imidacloprid 17.8 SL at 200 ml per acre for leaf curl, NIPHM gives 60 to 70 ml in 200 litres per acre. The NIPHM packages come from the central government plant protection institute and tell users to follow label claims, so we kept those numbers and left the TNAU dose out.
- **We kept a short list per disease** (one to three products) instead of copying every option, to keep the advice simple. Other products in the sources were left out on purpose, not because they are wrong.
- **Leaf mold has no chemical in the KB.** We did not find an Indian (ICAR, SAU or CIB&RC) recommendation with a dose. The two sources we used are from the US and UK, so we only took cultural steps from them. The app says "ask your KVK for the dose".
- **Some waiting periods are missing** (azoxystrobin, cyazofamid on tomato, cymoxanil plus mancozeb, cyantraniliprole, NSKE). The tables we read do not list them, so `waiting_days` is `null` and the app tells the farmer to check the label.
- **Yellow leaf curl.** Our class comes from datasets that call it tomato yellow leaf curl virus. TNAU and NIPHM describe tomato leaf curl virus (ToLCV), also spread by whitefly, which is what Indian farmers will see. We used the Indian advice.
- **Leaf miner.** We followed the serpentine leaf miner (Liriomyza trifolii) advice from TNAU and NIPHM. We did not check which leaf miner species is in the training photos.
- **ICAR-CPRI and ICAR-IIHR.** We tried to read ICAR-CPRI documents for potato, but the site did not respond from our machine, so nothing in the KB comes from CPRI directly. The Kufri varieties come from the TNAU and NIPHM pages.
- **CIB&RC.** We did not check each product against the live CIB&RC registration list. The NIPHM packages point users to label claims, but a registration can change, so the app always tells the farmer to read the label and ask the KVK.
- **Hindi.** All Hindi text was written by us, not taken from a source. Every entry has `"hindi_reviewed": false` until a Hindi speaker checks it.
