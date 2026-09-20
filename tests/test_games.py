import pytest

from authentic_dynamics import create_app


@pytest.mark.parametrize("path", ["/games", "/games/", "/games/maze-chase"])
def test_games_are_public_get_only_and_not_in_navigation(path):
    client = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()
    response = client.get(path)
    assert response.status_code == 200
    assert b"Maze Chase" in response.data
    assert client.post(path).status_code == 405
    html = response.get_data(as_text=True)
    nav = html.split('<nav id="nav"')[1].split('</nav>')[0]
    footer = html.split('<footer')[1]
    assert '/games' not in nav
    assert 'aria-current="page"' not in nav
    assert 'href="/games' not in footer
    assert b'href="/games/maze-chase"' in client.get('/games').data


def test_game_assets_are_local():
    client = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"}).test_client()
    for asset in ['css/games.css', 'js/games/maze-core.js', 'js/games/maze-chase.js']:
        assert client.get('/static/' + asset).status_code == 200
