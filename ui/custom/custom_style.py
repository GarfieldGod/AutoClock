from src.utils.const import Key

Text_Color = "grey"
Border_Width = "1px"
Border_Color = "#000000"
Border_Radius = Key.Empty
BackGround_Color = "#ffffff"

def get_group_css(css_data):
    background_color = css_data["BackGround_Color"] if css_data.get("BackGround_Color") is not None and css_data[
        "BackGround_Color"] != Key.Empty else BackGround_Color
    text_color = css_data["Text_Color"] if css_data.get("Text_Color") is not None and css_data[
        "Text_Color"] != Key.Empty else Text_Color
    border_color = css_data["Border_Color"] if css_data.get("Border_Color") is not None and css_data[
        "Border_Color"] != Key.Empty else Border_Color
    border_width = css_data["Border_Width"] if css_data.get("Border_Width") is not None and css_data[
        "Border_Width"] != Key.Empty else Border_Width
    css = f"""
        QGroupBox {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            font-weight: bold;
            font-size: 16px;
            background-color: {background_color};
            color: {text_color};
            border: {border_width} solid {border_color};
            border-radius: 5px;
            margin-top: 10px;
        }}
        QGroupBox:title {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            font-weight: bold;
            font-size: 24px;
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
    """
    return css