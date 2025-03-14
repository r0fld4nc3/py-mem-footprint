import argparse
import json
from collections import OrderedDict
from pathlib import Path

TEXTURE_PREFIX = "T"

MAPPING = {
    "D": "DXT5",
    "E": "DXT5",
    "M": "DXT5",
    "N": "DXT7",
    "ORM": "DXT5",
}

BYTES_PER_PIXEL = {
    "BC1": 0.5,  # DXT1
    "DXT1": 0.5,
    "BC3": 1.0,  # DXT5
    "DXT5": 1.0,
    "BC5": 1.0,
    "BC7": 1.0,  # DXT7
    "DXT7": 1.0,
}

MATERIAL_OVERHEADS = {
    "simple": 100 * 1024,  # 100 KB
    "medium": 100 * 1024,  # 150 KB
    "complex": 100 * 1024,  # 200 KB
}


SHADER_VARIANTS = {
    "simple": 2,  # Base + mobile
    "medium": 4,  # Base + mobile + high quality + distance field
    "complex": 8,  # Multiple quality levels and platforms
}

SHADER_SIZE_PER_VARIANT = 75 * 1024

MATERIAL_INSTANCE_OVERHEAD = 1.5 * 1024 * 1.5  # KB per instance

parser = argparse.ArgumentParser(description="")


def get_file_size(file_path):
    """Get the file size in bytes"""
    try:
        return Path(file_path).stat().st_size
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return 0


# Third-Party module-free approach to getting png dimensions
def get_image_size(file_path):
    """Get image dimensions without using external libraries"""
    with open(file_path, "rb") as f:
        str_file_path = str(file_path)
        # Read first few bytes to determine image type
        header = f.read(24)

        # JPEG
        if header.startswith(b"\xff\xd8"):
            f.seek(0)  # Go to start of file
            size = 2  # Skip the initial bytes
            while True:
                f.seek(size, 0)
                b = f.read(1)
                if not b or b[0] == 0xDA:  # Start of scan
                    break

                # Check for SOF marker (Start of Frame)
                elif b[0] == 0xC0 or b[0] == 0xC2:
                    f.seek(size + 5, 0)
                    height = f.read(2)
                    height = (height[0] << 8) + height[1]
                    width = f.read(2)
                    width = (width[0] << 8) + width[1]
                    return width, height

                size += 1

        # PNG
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            width = int.from_bytes(header[16:20], byteorder="big")
            height = int.from_bytes(header[20:24], byteorder="big")
            return width, height

        # TGA (Targa)
        # TGA doesn't have a standard magic number, so check file extension or other indicators
        elif str_file_path.lower().endswith(".tga") or any(
            header[1:3] == b
            for b in [
                b"\x00\x01",
                b"\x00\x02",
                b"\x00\x03",
                b"\x00\x09",
                b"\x00\x0a",
                b"\x00\x0b",
            ]
        ):
            # Width is at offset 12 (2 bytes)
            # Height is at offset 14 (2 bytes)
            width = int.from_bytes(header[12:14], byteorder="little")
            height = int.from_bytes(header[14:16], byteorder="little")
            return width, height

    # Format not recognized
    return None


def collect_dir_files(directory: Path) -> set[Path]:
    files = set()

    for item in directory.glob("**/*"):
        stem = item.stem
        t_type = stem.upper().split("_")[-1]
        prefix = stem.split("_", 1)[0]
        if prefix in TEXTURE_PREFIX and t_type in MAPPING.keys():
            files.add(directory / item)

    print(f"Collected {len(files)} files.")

    return files


def filter_files_to_materials(texture_files):
    # Mapping of texture name minus variant suffix "_D" or "_N"
    # Try to map how many textures comprise a material
    # Keys = Texture Name (no variant)
    # Values = Textures + Sizes
    result = OrderedDict(
        [
            ("materials", 0),
            ("total_textures", 0),
            ("total_disk_size", 0),
            ("mapping", OrderedDict()),
        ]
    )

    # Sort texture files for consistent ordering
    sorted_texture_files = sorted(texture_files, key=lambda x: str(x))

    for tex_path in sorted_texture_files:
        full_path = str(Path(tex_path).as_posix())
        file_size = get_file_size(tex_path)
        result["total_disk_size"] += file_size

        name_stem = Path(tex_path).stem

        # Parse the filename: T_TextureName_01_D -> base: T_TextureName_01, variant: D
        last_underscore_pos = name_stem.rfind("_")
        variant = name_stem[last_underscore_pos + 1 :]  # The suffix (D, ORM, etc.)
        base_name = name_stem[:last_underscore_pos]

        # Create base group if it doesn't exist
        if base_name not in result["mapping"]:
            result["mapping"][base_name] = {}
            result["materials"] += 1

        # Add this texture variant to its base group
        print(tex_path)
        result["mapping"][base_name][name_stem] = {
            "full_path": full_path,
            "size": get_image_size(tex_path),
            "bc": MAPPING.get(variant),
            "file_size_bytes": file_size,
            "file_size_mb": file_size / (1024 * 1024),
        }

        # Increment total texture count
        result["total_textures"] += 1

    return result


def calculate_texture_memory(width, height, compression_format, has_mipmaps=True):
    """Calculate memory footprint of a single texture"""
    # Base memory
    bpp = BYTES_PER_PIXEL.get(compression_format, 4.0)  # Default to uncompressed
    base_memory = width * height * bpp

    # Apply mipmap factor
    mipmap_factor = 1.33 if has_mipmaps else 1.0

    total_memory = base_memory * mipmap_factor

    return total_memory


def calculate_material_overhead(complexity="medium"):
    """Calculate the overhead of a master material"""
    base_material_memory = MATERIAL_OVERHEADS.get(
        complexity, MATERIAL_OVERHEADS["medium"]
    )
    shader_memory = (
        SHADER_VARIANTS.get(complexity, SHADER_VARIANTS["medium"])
        * SHADER_SIZE_PER_VARIANT
    )
    return base_material_memory + shader_memory


def calculate_footprint(materials_data, material_complexity="medium", has_mipmaps=True):
    """Calculate memory footprint for all materials"""

    result = OrderedDict(
        [
            (
                "master_material_overhead",
                calculate_material_overhead(material_complexity),
            ),
            ("instance_overhead_total", 0),
            ("texture_memory_total", 0),
            ("texture_disk_size_total", materials_data["total_disk_size"]),
            ("materials", OrderedDict()),
            ("summary", OrderedDict()),
        ]
    )

    # Sort material names for consistent ordering
    sorted_material_names = sorted(materials_data["mapping"].keys())

    # Calculate memory usage for each material
    for material_name in sorted_material_names:
        textures = materials_data["mapping"][material_name]
        material_result = OrderedDict(
            [
                ("instance_overhead", MATERIAL_INSTANCE_OVERHEAD),
                ("textures", OrderedDict()),
                ("total_texture_memory", 0),
                ("total_disk_size", 0),
            ]
        )

        # Sort texture names for consistent ordering
        sorted_texture_names = sorted(textures.keys())

        # Calculate memory for each texture in this material
        for texture_name in sorted_texture_names:
            texture_data = textures[texture_name]
            file_size = texture_data.get("file_size_bytes", 0)
            material_result["total_disk_size"] += file_size

            if texture_data["size"]:
                width, height = texture_data["size"]
                compression = texture_data["bc"]

                # Memory for this texture
                memory = calculate_texture_memory(
                    width, height, compression, has_mipmaps
                )

                material_result["textures"][texture_name] = OrderedDict(
                    [
                        ("full_path", texture_data.get("full_path")),
                        ("width", width),
                        ("height", height),
                        ("format", compression),
                        ("file_size_bytes", file_size),
                        ("file_size_mb", file_size / (1024 * 1024)),
                        ("memory_bytes", memory),
                        ("memory_mb", memory / (1024 * 1024)),
                    ]
                )

                # Add to total texture memory for this material
                material_result["total_texture_memory"] += memory
            else:
                print(f"Warning: Could not determine size for texture {texture_name}")
                material_result["textures"][texture_name] = OrderedDict(
                    [
                        ("full_path", texture_data.get("full_path")),
                        ("width", 0),
                        ("height", 0),
                        ("format", texture_data["bc"]),
                        ("file_size_bytes", file_size),
                        ("file_size_mb", file_size / (1024 * 1024)),
                        ("memory_bytes", 0),
                        ("memory_mb", 0),
                    ]
                )

        # Total memory for this material
        material_result["total_memory"] = (
            material_result["total_texture_memory"]
            + material_result["instance_overhead"]
        )
        material_result["total_texture_memory_mb"] = material_result[
            "total_texture_memory"
        ] / (1024 * 1024)
        material_result["total_memory_mb"] = material_result["total_memory"] / (
            1024 * 1024
        )
        material_result["total_disk_size_mb"] = material_result["total_disk_size"] / (
            1024 * 1024
        )

        # Add to result
        result["materials"][material_name] = material_result

        # Add to totals
        result["instance_overhead_total"] += material_result["instance_overhead"]
        result["texture_memory_total"] += material_result["total_texture_memory"]

    # Overall totals
    result["total_memory"] = (
        result["master_material_overhead"]
        + result["instance_overhead_total"]
        + result["texture_memory_total"]
    )

    # MB for summary
    result["summary"] = OrderedDict(
        [
            ("material_count", materials_data["materials"]),
            ("texture_count", materials_data["total_textures"]),
            (
                "master_material_overhead_mb",
                result["master_material_overhead"] / (1024 * 1024),
            ),
            (
                "instance_overhead_total_mb",
                result["instance_overhead_total"] / (1024 * 1024),
            ),
            ("texture_memory_total_mb", result["texture_memory_total"] / (1024 * 1024)),
            ("total_memory_mb", result["total_memory"] / (1024 * 1024)),
            ("total_memory_gb", result["total_memory"] / (1024 * 1024 * 1024)),
            ("total_disk_size_mb", result["texture_disk_size_total"] / (1024 * 1024)),
            (
                "total_disk_size_gb",
                result["texture_disk_size_total"] / (1024 * 1024 * 1024),
            ),
            (
                "disk_to_vram_ratio",
                (
                    (result["texture_memory_total"] / result["texture_disk_size_total"])
                    if result["texture_disk_size_total"]
                    else 0
                ),
            ),
        ]
    )

    return result


def parse_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    # Root Directory
    parser.add_argument(
        "root_dir",
        type=Path,
        default=Path.cwd(),
        nargs="?",
        help="Path to the system location (default: current working directory).",
    )

    args = parser.parse_args()

    return args


def main():
    args = parse_args(parser)
    print(f"'{args.root_dir}'")

    root = args.root_dir

    if not root or not Path(root).exists():
        print(f"Invalid path '{root}'")
        return False

    root = Path(root)

    if not root.is_dir():
        print(f"[DEBUG] Root is not dir. Getting current parent structure.")
        root = root.parent

    files_to_process = collect_dir_files(root)

    materials = filter_files_to_materials(files_to_process)

    print(json.dumps(materials, indent=2))
    print(
        f"{materials.get('materials')} materials from {materials.get('total_textures')} textures"
    )

    footprint = calculate_footprint(materials, material_complexity="medium")

    # Summary
    print("\n----- MEMORY FOOTPRINT SUMMARY -----")
    for key, value in footprint["summary"].items():
        pretty_key = " ".join(str(k).capitalize() for k in key.split("_"))
        if "mb" in key.lower():
            print(f"{pretty_key}: {value:.2f} MB")
        elif "gb" in key.lower():
            print(f"{pretty_key}: {value:.3f} GB")
        elif "ratio" in key.lower():
            print(f"{pretty_key}: {value:.2f}x")
        else:
            print(f"{pretty_key}: {value:.2f}")

    with open("material_memory_analysis.json", "w") as f:
        json.dump(footprint, f, indent=2)

    print(f"\nDetailed analysis saved to material_memory_analysis.json")


if __name__ == "__main__":
    main()
