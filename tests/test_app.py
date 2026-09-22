from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_demo_question_clear_and_isolation():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    button(app, '载入演示资料').click().run()
    assert not app.exception
    assert len(app.session_state.library.documents) == 3
    app.text_area(key='question_input').set_value('GPU 工作站提前多久预约')
    button(app, '检索资料').click().run()
    assert not app.exception
    assert app.session_state.answer.citations
    assert '24 小时' in app.session_state.pending['hits'][0].passage.text
    fresh = AppTest.from_file(str(APP), default_timeout=30).run()
    assert len(fresh.session_state.library.documents) == 0
    app.text_input(key='api_key').set_value('synthetic-test-key').run()
    button(app, '清空文档、回答和密钥').click().run()
    assert not app.exception
    assert len(app.session_state.library.documents) == 0
    assert app.session_state.api_key == ''
    assert 'answer' not in app.session_state


def test_missing_api_config_shows_error_without_crashing():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    button(app, '载入演示资料').click().run()
    app.text_area(key='question_input').set_value('图书借阅期限')
    button(app, '检索资料').click().run()
    button(app, '发送片段并生成回答').click().run()
    assert not app.exception
    assert len(app.error) > 0
