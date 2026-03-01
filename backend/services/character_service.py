import os

class CharacterService:
    """
    Service layer for handling CK3 Character file operations.
    """

    def save_character_history(self, script: str, output_path: str) -> str:
        """
        Saves the generated character script to a file with UTF-8 BOM encoding.

        Args:
            script (str): The CK3 formatted script string.
            output_path (str): The destination file path.

        Returns:
            str: The absolute path to the saved file.
        """
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(script)

        return os.path.abspath(output_path)
