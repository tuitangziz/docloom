import numpy as np
import pytest

from docloom.evaluation import evaluate
from docloom.library import Library


def test_bilingual_ranking_filter_and_no_answer():
    lib = Library()
    a, _ = lib.add('lab.md', 'GPU 工作站需要提前 24 小时预约。'.encode())
    b, _ = lib.add('food.txt', b'Orchard peaches are harvested in July.')
    assert lib.index.search('工作站预约')[0].passage.document_id == a.id
    assert lib.index.search('peaches harvest')[0].passage.document_id == b.id
    assert lib.index.search('peaches', document_ids={a.id}) == []
    assert lib.index.search('peaches', document_ids=set()) == []
    assert lib.index.search('quantum gluon scattering') == []
    assert lib.index.search('  ') == []


def test_optional_local_embedding_rank_and_validation():
    lib = Library()
    lib.add('a.txt', b'orchard apples')
    lib.add('b.txt', b'space rockets')
    lib.index.set_embeddings([[1, 0], [0, 1]], 'test-local-model')
    assert lib.index.search('spaceships', query_vector=[0, 1])[0].passage.filename == 'b.txt'
    with pytest.raises(ValueError):
        lib.index.search('spaceships', query_vector=[1, 0, 0])
    with pytest.raises(ValueError):
        lib.index.set_embeddings([[np.nan, 0], [0, 1]], 'bad')


def test_small_synthetic_retrieval_regression():
    report = evaluate()
    assert report['answerable_cases'] == 10
    assert report['hit_rate_at_3'] >= 0.9
    assert report['no_result_rate_on_unanswerable'] == 1.0
