#!/usr/bin/env python3
import os
import json
import asyncio
import aiohttp
import argparse
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

# List of files to ignore
IGNORE_FILES = {'.DS_Store', 'Thumbs.db', '.gitignore'}
# List of extensions to process
VALID_EXTENSIONS = {'.ppt', '.pptx', '.doc', '.docx', '.pdf', '.txt'}


class DocumentProcessor:
    def __init__(self, api_url: str, input_dir: str, output_dir: str):
        self.api_url = api_url.rstrip('/')
        # Expand user directory and resolve relative paths
        self.input_dir = Path(os.path.expanduser(input_dir)).resolve()
        self.output_dir = Path(os.path.expanduser(output_dir)).resolve()

        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for json and markdown files
        self.json_dir = self.output_dir / 'json'
        self.md_dir = self.output_dir / 'markdown'
        self.json_dir.mkdir(exist_ok=True)
        self.md_dir.mkdir(exist_ok=True)

        print(f"Input directory: {self.input_dir}")
        print(f"Output directory: {self.output_dir}")

    def should_process_file(self, file_path: Path) -> bool:
        """Check if the file should be processed based on name and extension"""
        if file_path.name in IGNORE_FILES:
            return False
        if file_path.suffix.lower() not in VALID_EXTENSIONS:
            return False
        return True

    def get_safe_filename(self, filename: str) -> str:
        """Convert filename to safe version without spaces"""
        return filename.replace(' ', '_')

    def get_relative_path(self, file_path: Path) -> Path:
        """Get the relative path from input directory to the file"""
        return file_path.relative_to(self.input_dir)

    async def process_single_file(self, file_path: Path, session: aiohttp.ClientSession) -> Optional[dict]:
        """Process a single file through the API"""
        try:
            # Prepare the file for upload
            data = aiohttp.FormData()
            data.add_field('file',
                           open(file_path, 'rb'),
                           filename=file_path.name,
                           content_type='application/octet-stream')

            # Make the API request
            async with session.post(f'{self.api_url}/parse_document/ppt',
                                    data=data) as response:
                if response.status != 200:
                    print(f"Error processing {file_path}: {response.status}")
                    return None

                return await response.json()

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None

    async def save_outputs(self, file_path: Path, response_data: dict):
        """Save JSON and markdown outputs maintaining directory structure"""
        # Get relative path from input directory
        rel_path = self.get_relative_path(file_path)
        safe_filename = self.get_safe_filename(file_path.stem)

        # Create subdirectories if they don't exist
        json_subdir = self.json_dir / rel_path.parent
        md_subdir = self.md_dir / rel_path.parent
        json_subdir.mkdir(parents=True, exist_ok=True)
        md_subdir.mkdir(parents=True, exist_ok=True)

        # Save JSON response
        json_path = json_subdir / f"{safe_filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)

        # Extract and save text as markdown
        if 'text' in response_data:
            md_path = md_subdir / f"{safe_filename}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(response_data['text'])

    def get_all_files(self) -> List[Path]:
        """Recursively get all files from input directory"""
        files = []
        for file_path in self.input_dir.rglob('*'):
            if file_path.is_file() and self.should_process_file(file_path):
                files.append(file_path)
        return files

    async def process_directory(self):
        """Process all files in the input directory and its subdirectories"""
        files = self.get_all_files()
        total_files = len(files)

        if total_files == 0:
            print(f"No processable files found in {self.input_dir}")
            return

        print(f"Found {total_files} files to process")

        async with aiohttp.ClientSession() as session:
            for idx, file_path in enumerate(files, 1):
                rel_path = self.get_relative_path(file_path)
                print(f"Processing [{idx}/{total_files}]: {rel_path}")

                response_data = await self.process_single_file(file_path, session)
                if response_data:
                    await self.save_outputs(file_path, response_data)
                    print(f"Successfully processed: {rel_path}")
                else:
                    print(f"Failed to process: {rel_path}")


def validate_url(url: str) -> str:
    """Validate the API URL format"""
    try:
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            return url
        raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid URL format: {url}")


def expand_path(path: str) -> str:
    """Expand user and resolve relative paths"""
    expanded = os.path.expanduser(path)
    resolved = os.path.abspath(expanded)
    return resolved


def main():
    parser = argparse.ArgumentParser(description='Process documents through API and save outputs')
    parser.add_argument('--api-url', type=validate_url, required=True,
                        help='API endpoint URL (e.g., http://example.com:8000)')
    parser.add_argument('--input-dir', type=str, required=True,
                        help='Input directory containing files to process (supports ~ and relative paths)')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Output directory for processed files (supports ~ and relative paths)')

    args = parser.parse_args()

    try:
        processor = DocumentProcessor(args.api_url, args.input_dir, args.output_dir)
        asyncio.run(processor.process_directory())
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
