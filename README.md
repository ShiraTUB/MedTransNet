# MedGraphTrans
A model architecture which utilizes a medical KG to enrich the prompt of an instructional LLM.

## Installation
`pip install -r requirements.txt`

- A `.env` file with your OpenAI key in the format: 
    `OPENAI_API_KEY=OPENAI_API_KEY=sk-xxxxxxxxx` is expected at the top level folder
    ```
    MedTransNet/
    ``` 

## Usage and Data


### Knowledge Graph Generation
A Knowledge Graph Generation file can be found under `MedTransNet/src/preprocess/primeKG_generation.py`.

The Knowledge Graph used in this project is [PrimeKG](https://www.nature.com/articles/s41597-023-01960-3).

- The necessary data needed for this step can be bound under [PrimeKG csv file](https://dataverse.harvard.edu/api/access/datafile/6180620).
 
### Building the raw dataset
The next step in the pipeline is using PrimeKG together with [MedMCQA, a large-scale, Multiple-Choice Question Answering (MCQA) dataset](https://medmcqa.github.io/) to create the raw training and evaluation dataset. Each question in MedMCQA is turned into a heterogeneous graph, with knowledge nodes extracted from PrimeKG appended to it. The relevant file can be found under 
`src/preprocess/build_raw_dataset.py`. 

The necessary data needed for this step can be bound under:
- [prime_kg_nx_63960.pickle](https://drive.google.com/file/d/1-Zj4-essj2AuuGC97Lc5XPRF0dWfkuNh/view?usp=drive_link)
- [prime_kg_embeddings_tensor_63960.pt](https://drive.google.com/file/d/1-SqPAh3okLm9VFSl3tEkEmSNmUKopuyz/view?usp=drive_link)

### Training the model

The model developed in this project can be found under `MedTransNet/src/medical_hgt`.

The necessary data needed for this step can be bound under:
1. [prime_kg_nx_63960.pickle](https://drive.google.com/file/d/1-Zj4-essj2AuuGC97Lc5XPRF0dWfkuNh/view?usp=drive_link) - Can be generated using the `MedTransNet/src/preprocess/primeKG_generation.py` file.
2. [llm_feedbacks_6102.pickle](https://drive.google.com/file/d/131t7p-6xVLQa-yA2hbJ3yxiW17P2ZAdx/view?usp=drive_link) - Can be generated using the `MedTransNet/src/medical_hgt/llm.py` file.
3. [subgraphs_dict_val.pickle](https://drive.google.com/file/d/1-zSfsX-3GpmXTSTp2s8TewkWcwR9cFmU/view?usp=drive_link)
4. [train_mini_batches_32_cpu.pickle](https://drive.google.com/file/d/1YpJtQ-1sXZeFu66DmD-j1GAZ-SvNm6uH/view?usp=drive_link)
5. [val_mini_batches_32_cpu.pickle](https://drive.google.com/file/d/1-26H8rMOECEVmUhxuwdpB9o3udI5R2-T/view?usp=sharing)
6. [test_mini_batches_32_cpu.pickle](https://drive.google.com/file/d/1-5zcojOgiPn7KXP5IGm1I2i7Jt4N4X-H/view?usp=drive_link)

* Files 3. to 6. can be generated using the `MedTransNet/src/medical_hgt/dataset_builder.py` file.


### It is expected that all downloaded files will be saved under the following path: 
    ```
    MedGraphTrans/datasets
    ```

#### This project is developed as a Bachelor's Thesis in the Technical University of Berlin. Wo