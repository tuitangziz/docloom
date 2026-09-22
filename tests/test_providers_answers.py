import json

import httpx
import pytest

from docloom.answers import export_json, export_markdown, generate_answer, source_packet
from docloom.library import Library
from docloom.providers import CompatibleAPI, OllamaProvider, ProviderError, validate_url


@pytest.fixture
def hits():
    library = Library()
    library.add('private-filename.txt', b'The orchard opens at nine every morning. Apples are available.')
    return library.index.search('orchard opens')


def reply(**kwargs):
    data = {'answer': 'The orchard opens at nine. [S1]', 'citations': [{'source_id': 'S1', 'quote': 'The orchard opens at nine every morning.'}], 'insufficient_evidence': False}
    data.update(kwargs)
    return json.dumps(data)


class FakeModel:
    def __init__(self, text): self.text = text
    def complete(self, messages): return self.text


def test_api_auth_payload_and_citations(hits):
    def handler(request):
        assert request.url == 'https://provider.example/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer synthetic-test-credential'
        body = json.loads(request.content)
        assert body['model'] == 'test-model'
        assert 'private-filename.txt' not in request.content.decode()
        assert 'The orchard' in body['messages'][1]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': reply()}}]})
    provider = CompatibleAPI('https://provider.example/v1/', 'test-model', 'synthetic-test-credential', httpx.MockTransport(handler))
    assert 'synthetic-test-credential' not in repr(provider)
    answer = generate_answer('When does the orchard open?', hits, provider)
    assert answer.mode == '模型回答'
    assert answer.citations[0].filename == 'private-filename.txt'
    assert 'synthetic-test-credential' not in export_json('question', answer)


@pytest.mark.parametrize('raw', [reply(citations=[{'source_id':'S9','quote':'The orchard opens at nine every morning.'}]), reply(citations=[{'source_id':'S1','quote':'The orchard opens at midnight.'}]), reply(answer='No markers.'), reply(answer='Wrong marker. [S2]'), 'not JSON'])
def test_bad_references_fail_closed(hits, raw):
    answer = generate_answer('question', hits, FakeModel(raw))
    assert answer.mode == '原文检索'
    assert answer.warnings


def test_no_evidence_never_calls_api(hits):
    class Never:
        def complete(self, messages): raise AssertionError('Should not be called')
    assert generate_answer('question', [], Never()).refused
    assert generate_answer('question', hits, FakeModel(reply(insufficient_evidence=True, citations=[]))).refused
    assert 'private-filename' not in json.dumps(source_packet('question', hits))


@pytest.mark.parametrize('url', ['http://remote.example/v1', 'https://name:secret@remote.example/v1', 'https://remote.example/v1?key=secret', 'file:///tmp/model', 'https://remote.example/#token'])
def test_unsafe_api_urls_rejected(url):
    with pytest.raises(ProviderError): validate_url(url)


def test_ollama_is_local_and_compatible(hits):
    seen = []
    def handler(request):
        seen.append(request.url.path)
        body = json.loads(request.content)
        assert 'authorization' not in request.headers
        if request.url.path == '/api/show': return httpx.Response(200, json={'capabilities':['completion']})
        assert body['stream'] is False
        return httpx.Response(200, json={'message':{'content':reply()}})
    p = OllamaProvider('http://localhost:11434', 'test:4b', httpx.MockTransport(handler))
    assert generate_answer('question', hits, p).mode == '模型回答'
    assert seen == ['/api/show', '/api/chat']
    with pytest.raises(ProviderError): OllamaProvider('https://remote.example', 'test')
    with pytest.raises(ProviderError): OllamaProvider(model='model:cloud')


def test_remote_ollama_alias_never_receives_documents(hits):
    def handler(request):
        assert request.url.path == '/api/show'
        return httpx.Response(200, json={'remote_host':'https://remote.example'})
    answer = generate_answer('question', hits, OllamaProvider(transport=httpx.MockTransport(handler)))
    assert answer.mode == '原文检索'


@pytest.mark.parametrize('status', [302, 401, 429, 500])
def test_errors_do_not_echo_credentials_or_provider_body(hits, status):
    def handler(request):
        return httpx.Response(status, text='sensitive echoed secret', headers={'Location':'https://elsewhere.example'})
    provider = CompatibleAPI('https://provider.example/v1', 'model', 'synthetic-secret', httpx.MockTransport(handler))
    answer = generate_answer('question', hits, provider)
    assert answer.mode == '原文检索'
    assert 'secret' not in ' '.join(answer.warnings)


def test_timeout_is_readable(hits):
    def handler(request): raise httpx.ReadTimeout('internal sensitive details')
    provider = CompatibleAPI('https://provider.example/v1', 'model', 'synthetic-secret', httpx.MockTransport(handler))
    assert '超时' in generate_answer('question', hits, provider).warnings[0]


def test_export_does_not_create_active_remote_image(hits):
    answer = generate_answer('q', hits, FakeModel(reply()))
    output = export_markdown('![tracking](https://example.invalid/image)', answer)
    assert '![tracking](' not in output
