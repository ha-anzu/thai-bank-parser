from typer.testing import CliRunner

from thai_bank_parser.cli import app


runner = CliRunner()


def test_templates_command_renders_brand_and_templates():
    result = runner.invoke(app, ["templates"])

    assert result.exit_code == 0
    assert "THAI BANK PARSER" in result.output
    assert "Template Bay" in result.output
    assert "krungsri" in result.output


def test_start_menu_can_quit():
    result = runner.invoke(app, ["start"], input="q\n")

    assert result.exit_code == 0
    assert "command deck" in result.output
    assert "red panda clerk signing off" in result.output
