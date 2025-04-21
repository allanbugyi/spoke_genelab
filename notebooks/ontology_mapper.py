"""
This module provides functions to map terms to concepts in an ontology.

Author: Peter W Rose (pwrose@ucsd.edu)
Created: 2024-03-03
"""
import os
import requests
from dotenv import load_dotenv
import time
import pandas as pd
import inflection

CHUNK_SIZE = 50

def map_ontology(df, input_col, output_col, ontology, apikey):
    """
    Map terms from a DataFrame column to concepts in an ontology.

    Parameters
    ----------
    df (pandas.DataFrame): The DataFrame containing the data to be mapped.
    input_col (str): The name of the column in `df` containing terms to be mapped.
    output_col (str): The name of the column in `df` to store the mapped ontology concepts.
    ontology (Ontology): Name of the ontology

    Returns
    -------
    pandas.DataFrame: The DataFrame with mapped ontology concepts in the `output_col` column.

    Notes
    -----
    Make sure to set the `BIOPORTAL_API_KEY` variable in the .env file.
    Create a BioPortal account to get an API key.

    Example
    -------
    >>> import os
    >>> import pandas as pd
    >>> from dotenv import load_dotenv
    >>> import ontology_mapper
    >>>
    >>> # get BioPortal API key
    >>> load_dotenv(<path to .env file>)
    >>> apikey = os.getenv("BIOPORTAL_API_KEY")
    >>>
    >>> # Sample DataFrame (may contain other columns)
    >>> df = pd.DataFrame({"terms": ["liver", "brain", "zygote"]})
    >>> mapped_df = ontology_mapper.map_ontology(df, "terms", "mapped_concepts", "UBERON", apikey)
    >>> print(mapped_df)
            terms     mapped_concepts
    0       liver     UBERON:0002107
    1       brain     UBERON:0000955
    2      zygote     CL:0010017
    
    """

    # convert to lowercase and map to ontology
    df["__lower__"] = df[input_col].str.lower()

    # remove misc characters that interfere with ontology matching
    df["__lower__"] = df["__lower__"].str.replace("-", " ")
    df["__lower__"] = df["__lower__"].str.replace(r'\(.*?\)', '', regex=True)

    # cleanup special cases from GeneLab
    if ontology == "UBERON":
        df["__lower__"] = df["__lower__"].str.replace("human", "")
        df["__lower__"] = df["__lower__"].str.replace("murine", "")
        df["__lower__"] = df["__lower__"].str.replace("male", "")
        df["__lower__"] = df["__lower__"].str.replace("female", "")
        df["__lower__"] = df["__lower__"].str.replace("carcass", "")
        df["__lower__"] = df["__lower__"].str.replace("tissue", "")
        df["__lower__"] = df["__lower__"].str.replace("mandibular bone", "mandible")
        df["__lower__"] = df["__lower__"].str.replace("left lobe of the liver", "liver left lateral lobe")

    df["__lower__"] = df["__lower__"].str.strip()
    
    df = map_column_new(df, "__lower__", ontology, apikey)

    # remove anatomical positions and other prefixes to match UEBERON ontology classes
    df["__nopos__"] = df["__lower__"]
    if ontology == "UBERON":
        df["__nopos__"] = df["__nopos__"].str.replace("left" , "")
        df["__nopos__"] = df["__nopos__"].str.replace("right", "")
        df["__nopos__"] = df["__nopos__"].str.replace("both sides", "")
        df["__nopos__"] = df["__nopos__"].str.replace("medial", "")
        df["__nopos__"] = df["__nopos__"].str.replace("distal", "")
        df["__nopos__"] = df["__nopos__"].str.replace("peripheral", "")
        df["__nopos__"] = df["__nopos__"].str.replace("dorsal", "")
        df["__nopos__"] = df["__nopos__"].str.replace("lateral", "")
        df["__nopos__"] = df["__nopos__"].str.replace("4th", "")
        df["__nopos__"] = df["__nopos__"].str.replace("femoral", "")
        df["__nopos__"] = df["__nopos__"].str.replace("ventricular", "")
        df["__nopos__"] = df["__nopos__"].str.replace("primary", "")
        df["__nopos__"] = df["__nopos__"].str.replace("partial", "")
        df["__nopos__"] = df["__nopos__"].str.replace("whole", "")
        df["__nopos__"] = df["__nopos__"].str.replace("lobe of the", "lobe of")
        df["__nopos__"] = df["__nopos__"].str.replace("3d", "") # 3d cells


    df["__nopos__"] = df["__nopos__"].str.strip()
    #print(df[["__nopos__"]].head())
    df = map_column_new(df, "__nopos__", ontology, apikey)

    # convert plural to singular terms and map to ontology
    df["__nopos__singular__"] = df["__nopos__"].apply(lambda x: inflection.singularize(x))
    df = map_column_new(df, "__nopos__singular__", ontology, apikey)
    
    df["__singular__"] = df["__lower__"].apply(lambda x: inflection.singularize(x))
    df = map_column_new(df, "__singular__", ontology, apikey)


    # Create output columns
    output_id_col = output_col + "_id"
    output_name_col = output_col + "_name"
    output_uri_col = output_col + "_uri"
    
    # coalesce mappings
    df[output_uri_col] = df[["__id__lower__", "__id__nopos__", "__id__nopos__singular__", "__id__singular__"]].copy().bfill(axis=1).iloc[:, 0]
    df[output_name_col] = df[["__name__lower__", "__name__nopos__", "__name__nopos__singular__", "__name__singular__"]].copy().bfill(axis=1).iloc[:, 0]
    
    # drop temporary columns
    df.drop(columns=["__lower__", "__nopos__", "__nopos__singular__", "__singular__", 
                     "__id__lower__", "__id__nopos__", "__id__nopos__singular__", "__id__singular__",
                     "__name__lower__", "__name__nopos__", "__name__nopos__singular__", "__name__singular__",
                    ], inplace=True)
    
    df[output_uri_col] = df[output_uri_col].fillna("")
    df[output_name_col] = df[output_name_col].fillna("")

    # convert URI to CURIE
    df[output_id_col] = df[output_uri_col].str.replace("http://purl.obolibrary.org/obo/", "", regex=False)
    df[output_id_col] = df[output_id_col].str.replace("_", ":", regex=False)
    
    return df
    

# def map_column(df, column, ontology, apikey):
#     terms = list(df[column].unique())
#     map = match_terms(terms, column, ontology, apikey) 
#     df = df.merge(map, on=column, how="left")
#     return df


def map_column_new(df, column, ontology, apikey):
    terms = list(df[column].unique())

    # BioPortal recommender can only handle a small number of terms at a time. 
    # Run it in small chunks
    chunks = create_chunks(terms, CHUNK_SIZE)

    dfs = []
    for chunk in chunks:
        mapped_terms = match_terms(chunk, column, ontology, apikey)
        dfs.append(mapped_terms)

    mapped_df = pd.concat(dfs)
    
    df = df.merge(mapped_df, on=column, how="left")
    return df


def create_chunks(data, chunk_size):
    """
    Split a list into smaller chunks of a specified size.

    Args:
        data (list): The input list to be divided into chunks.
        chunk_size (int): The maximum size of each chunk.

    Returns:
        list: A list of chunks, where each chunk is a sublist of 'data'.

    Example:
        >>> data = [1, 2, 3, 4, 5, 6, 7, 8]
        >>> chunk_size = 3
        >>> create_chunks(data, chunk_size)
        [[1, 2, 3], [4, 5, 6], [7, 8]]
    """
    # split list into chunks of max size: chunk_size
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    

def match_terms(terms, label, ontology, apikey):
    data = get_recommendation(terms, ontology, apikey)
    id_col = f"__id{label}"
    name_col = f"__name{label}"
    
    if len(data) > 0:
        match = pd.json_normalize(data[0]["coverageResult"], record_path="annotations", errors="ignore")
        match.rename(columns={"text": label, "annotatedClass.@id": id_col}, inplace=True)
        match[label] = match[label].str.lower()
        match[name_col] = match[label]
        match = match[[label, id_col, name_col]].copy()
    else:
        #print("empty data:", data)
        match = pd.DataFrame(columns=[label, id_col, name_col])
  
    return match


def get_recommendation(terms, ontologies, apikey):
    """
    Get ontology recommendations based on input terms.

    Parameters
    ----------
    terms : str
        Input terms for which ontology recommendations are needed.
        Can be a single term or a list of terms separated by comma.
    ontologies : str
        Ontologies to consider for recommendations.
        Can be a single ontology or a list of ontologies separated by comma.
    apikey : str
        BipPortal API key.

    Returns
    -------
    dict
        A dictionary containing ontology recommendations based on the input terms.

    Raises
    ------
    requests.exceptions.HTTPError
        If the HTTP request to the recommender API fails (e.g., invalid API key, server error).
    requests.exceptions.RequestException
        If there is a general request exception while communicating with the recommender API.

    Notes
    -----
    This function sends a POST request to the BioPortal Recommender API
    (https://bioportal.bioontology.org/recommender) to get ontology recommendations
    based on the provided input terms and ontologies.

    The API requires authentication via an API key, and the function uses the provided API key
    for authorization. Make sure to set the 'APIKEY' variable with a valid BioPortal API key
    before calling this function. Create a BioPortal account to get an API key.

    Example
    -------
    >>> APIKEY = "your_api_key"
    >>> terms = ["apple", "orange"]
    >>> ontologies = "FOODON"
    >>> recommendations = get_recommendation(terms, ontologies, APIKEY)
    """
    time.sleep(0.5)
    
    URL = "https://data.bioontology.org/recommender"
    HEADERS = {"accept": "application/json", "Authorization": f"apikey token={apikey}"}
    terms_string = ",".join(terms)

    params = {"input": terms_string, "input_type": "2", "ontologies": ontologies}

    try:
        response = requests.post(URL, headers=HEADERS, json=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: {error}")
        raise
    except requests.exceptions.RequestException as error:
        print(f"ERROR: {error}")
        raise

    return data
