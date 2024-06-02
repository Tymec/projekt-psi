from __future__ import annotations

import bz2
from typing import TYPE_CHECKING, Literal

import pandas as pd
import spacy
from tqdm import tqdm

from app.constants import (
    AMAZONREVIEWS_PATH,
    AMAZONREVIEWS_URL,
    IMDB50K_PATH,
    IMDB50K_URL,
    SENTIMENT140_PATH,
    SENTIMENT140_URL,
    TEST_DATASET_PATH,
    TEST_DATASET_URL,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc

__all__ = ["load_data", "tokenize"]


try:
    nlp = spacy.load("en_core_web_sm", disable=["tok2vec", "parser", "ner"])
except OSError:
    print("Downloading spaCy model...")

    from spacy.cli import download as spacy_download

    spacy_download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm", disable=["tok2vec", "parser", "ner"])


def _lemmatize(doc: Doc, threshold: int = 2) -> list[str]:
    """Lemmatize the provided text using spaCy.

    Args:
        doc: spaCy document
        threshold: Minimum character length of tokens

    Returns:
        Lemmatized text
    """
    return [
        token.lemma_.lower().strip()
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.like_email
        and not token.like_url
        and not token.like_num
        and not (len(token.lemma_) < threshold)
    ]


def tokenize(
    text_data: list[str],
    batch_size: int = 512,
    n_jobs: int = 4,
    character_threshold: int = 2,
    show_progress: bool = True,
) -> list[list[str]]:
    """Tokenize the provided text using spaCy.

    Args:
        text_data: Text data to tokenize
        batch_size: Batch size for tokenization
        n_jobs: Number of parallel jobs
        character_threshold: Minimum character length of tokens
        show_progress: Whether to show a progress bar

    Returns:
        Tokenized text data
    """
    return [
        _lemmatize(doc, character_threshold)
        for doc in tqdm(
            nlp.pipe(text_data, batch_size=batch_size, n_process=n_jobs),
            total=len(text_data),
            disable=not show_progress,
            unit="doc",
        )
    ]


def load_sentiment140(include_neutral: bool = False) -> tuple[list[str], list[int]]:
    """Load the sentiment140 dataset and make it suitable for use.

    Args:
        include_neutral: Whether to include neutral sentiment

    Returns:
        Text and label data

    Raises:
        FileNotFoundError: If the dataset is not found
    """
    # Check if the dataset exists
    if not SENTIMENT140_PATH.exists():
        msg = (
            f"Sentiment140 dataset not found at: '{SENTIMENT140_PATH}'\n"
            "Please download the dataset from:\n"
            f"{SENTIMENT140_URL}"
        )
        raise FileNotFoundError(msg)

    # Load the dataset
    data = pd.read_csv(
        SENTIMENT140_PATH,
        encoding="ISO-8859-1",
        names=[
            "target",  # 0 = negative, 2 = neutral, 4 = positive
            "id",  # The id of the tweet
            "date",  # The date of the tweet
            "flag",  # The query, NO_QUERY if not present
            "user",  # The user that tweeted
            "text",  # The text of the tweet
        ],
    )

    # Ignore rows with neutral sentiment
    if not include_neutral:
        data = data[data["target"] != 2]

    # Map sentiment values
    data["sentiment"] = data["target"].map(
        {
            0: 0,  # Negative
            4: 1,  # Positive
            2: 2,  # Neutral
        },
    )

    # Return as lists
    return data["text"].tolist(), data["sentiment"].tolist()


def load_amazonreviews() -> tuple[list[str], list[int]]:
    """Load the amazonreviews dataset and make it suitable for use.

    Returns:
        Text and label data

    Raises:
        FileNotFoundError: If the dataset is not found
    """
    # Check if the dataset exists
    if not AMAZONREVIEWS_PATH.exists():
        msg = (
            f"Amazonreviews dataset not found at: '{AMAZONREVIEWS_PATH}'\n"
            "Please download the dataset from:\n"
            f"{AMAZONREVIEWS_URL}"
        )
        raise FileNotFoundError(msg)

    # Load the dataset
    with bz2.BZ2File(AMAZONREVIEWS_PATH) as f:
        dataset = [line.decode("utf-8") for line in f]

    # Split the data into labels and text
    labels, texts = zip(*(line.split(" ", 1) for line in dataset))

    # Map sentiment values
    sentiments = [int(label.split("__label__")[1]) - 1 for label in labels]

    # Return as lists
    return texts, sentiments


def load_imdb50k() -> tuple[list[str], list[int]]:
    """Load the imdb50k dataset and make it suitable for use.

    Returns:
        Text and label data

    Raises:
        FileNotFoundError: If the dataset is not found
    """
    # Check if the dataset exists
    if not IMDB50K_PATH.exists():
        msg = (
            f"IMDB50K dataset not found at: '{IMDB50K_PATH}'\n"
            "Please download the dataset from:\n"
            f"{IMDB50K_URL}"
        )  # fmt: off
        raise FileNotFoundError(msg)

    # Load the dataset
    data = pd.read_csv(IMDB50K_PATH)

    # Map sentiment values
    data["sentiment"] = data["sentiment"].map(
        {
            "positive": 1,
            "negative": 0,
        },
    )

    # Return as lists
    return data["review"].tolist(), data["sentiment"].tolist()


def load_test(include_neutral: bool = False) -> tuple[list[str], list[int]]:
    """Load the test dataset and make it suitable for use.

    Args:
        include_neutral: Whether to include neutral sentiment

    Returns:
        Text and label data

    Raises:
        FileNotFoundError: If the dataset is not found
    """
    # Check if the dataset exists
    if not TEST_DATASET_PATH.exists():
        msg = (
            f"Test dataset not found at: '{TEST_DATASET_PATH}'\n"
            "Please download the dataset from:\n"
            f"{TEST_DATASET_URL}"
        )
        raise FileNotFoundError(msg)

    # Load the dataset
    data = pd.read_csv(TEST_DATASET_PATH)

    # Ignore rows with neutral sentiment
    if not include_neutral:
        data = data[data["label"] != 1]

    # Map sentiment values
    data["label"] = data["label"].map(
        {
            0: 0,  # Negative
            1: 1,  # Neutral
            2: 2,  # Positive
        },
    )

    # Return as lists
    return data["text"].tolist(), data["label"].tolist()


def load_data(dataset: Literal["sentiment140", "amazonreviews", "imdb50k", "test"]) -> tuple[list[str], list[int]]:
    """Load and preprocess the specified dataset.

    Args:
        dataset: Dataset to load

    Returns:
        Text and label data

    Raises:
        ValueError: If the dataset is not recognized
    """
    match dataset:
        case "sentiment140":
            return load_sentiment140(include_neutral=False)
        case "amazonreviews":
            return load_amazonreviews()
        case "imdb50k":
            return load_imdb50k()
        case "test":
            return load_test(include_neutral=False)
        case _:
            msg = f"Unknown dataset: {dataset}"
            raise ValueError(msg)
