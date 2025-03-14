Unreal Engine typically uses block-compressed texture formats (e.g.: DXT/BC formats), which have fixed compression ratios.

# DXT5 (BC3):
- **Compressed size:**   8 bits (1 byte) per texel.
- **Compression ratio**: 4:1 (compared to uncompressed RGBA8888)
- **Memory per pixel**:  1 byte

# DXT7 (BC7):
- **Compressed size**:   8 bits (1 byte) per texel.
- **Compression ratio**: 4:1
- **Memory per pixel**:  1 byte
- Typically used for high-quality normal maps and other data

```
Memory (bytes) = Width x Height x Bytes per Texel x (1 p Mipmap Factor)
```

- **Bytes per Texel**: Depends on the compression format (1 byte per texel for DXT5 and DXT7)
- **Mipmap Factor**: Mipmaps add approx. 33% to texture size, meaning the total footprint is roughly 1.33 x base size.

## Example 2K (DXT5 or DXT7):
- **Resolution**:     2048 x 2048
- **Bytes p/ Texel**: 1
- **Base Size**: 2048 x 2048 x 1 = 4,194,304 bytes (4 MB)
- **Inlcude Mipmaps**: 4,194,304 x 1.33 ~= 5,579,424 bytes (~5.58 MB).

## Example 4K (DXT5 or DXT7):
- **Resolution**:     4096 x 4096
- **Bytes p/ Texel**: 1
- **Base Size**: 4096 x 4096 x 1 = 16,777,216 bytes (16 MB)
- **Inlcude Mipmaps**: 16,777,216 x 1.33 ~= 22,360,064 bytes (~22.36 MB).

## Scaling to All Textures
**To calculate VRAM usage for all textures we can sum up the memory footprints for each one:**

- **10 textures at 2K using DXT5:**
    10 x 5.58 MB = 55.8 MB

- **5 textures at 4K using DXT7:**
    5 x 22.36 MB = 111.8 MB

- **Total**: 55.8 + 111.8 = 167 MB


# Understanding the Texture Slots and Their Compression

**Color (RGB)**: Typically stored as BC7 (DXT7) for high-quality color data.

**OcclusionRoughnessMetallic (ORM)**: Packed texture, typically stored as BC1 (DXT1) since it's grayscale data packed into RGB channels.

**Normals**: Typically stored as BC5 (DXT5) for two-channel normal data (R and G).

**Emissive**: Typically stored as BC7 (DXT7) for high-quality emissive color.

**Mask (M)**: Custom mask texture, typically stored as BC1 (DXT1) for grayscale or packed data.

| Map Type                         | Compression Format | Bytes per Texel | Notes                                   |
|----------------------------------|--------------------|-----------------|-----------------------------------------|
| Color (RGB)                      | BC7 (DXT7)         | 1               | High-quality color data.                |
| OcclusionRoughnessMetallic (ORM) | BC1 (DXT1)         | 0.5             | Packed grayscale data into RGB channels.|
| Normals                          | BC5 (DXT5)         | 1               | Two-channel normal data (R and G).      |
| Emissive                         | BC7 (DXT7)         | 1               | High-quality emissive color.            |
| Mask (M)                         | BC1 (DXT1)         | 0.5             | Grayscale or packed data.               |



# Calculate Memory Impact For Each Texture

- **Color (RGB)**: 2048 x 2048 x 1 x 1.33   = 5,579,424 bytes (~5.58 MB).
- **ORM**:         2048 x 2048 x 0.5 x 1.33 = 2,789,712 bytes (~2.79 MB).
- **Normals**:     2048 x 2048 x 1 x 1.33   = 5,579,424 bytes (~5.58 MB).
- **Emissive**:    2048 x 2048 x 1 x 1.33   = 5,579,424 bytes (~5.58 MB).
- **Mask (M)**:    2048 x 2048 x 0.5 x 1.33 = 2,789,712 bytes (~2.79 MB).

In this case, for a single material with 2K textures

C       ORM   Nrm    Emiss  Mask
5.58 + 2.79 + 5.58 + 5.58 + 2.79 = 22.32MB

If we have **30 assets**, each with unique textures, using the same maps, on average:
- 22.32 MB x 30 = 669.6 MB

# Unreal Engine Material + Shader Calculation

## Material Memory Components

A material in Unreal Engine consumes memory through:

- Texture maps (which we've already calculated)
- Material parameter data
- Shader compilation data
- Material instance overhead

--- 

- **Color (RGB)** - typically BC3/DXT5
- **OcclusionRoughnessMetallic (ORM)** - typically BC3/DXT5
- **Normals** - typically BC7/DXT7
- **Emissive** - typically BC3/DXT5
- **M map (masks)** - typically BC3/DXT5


## Material Parameter and Shader Memory

For a basic material with these maps plugged into their respective slots, we can estimate:

- **Base material overhead**: ~100-200 KB
- **Compiled shader variants**: ~50-100 KB per shader variant
- **Material instance overhead**: ~1-2 KB per instance


## Asset Calculation

Let's take an example of a single asset with 5 texture maps at 2K resolution:

1. **Texture Memory**:


- **Color (RGB)**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **ORM**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **Normal**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT7)
- **Emissive**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **Mask**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **Total Texture Memory**: ~26.65 MB

2. **Material Overhead**:

- **Base material**: ~150 KB
- **Shader variants (4)**: ~300 KB
- **Instance Overhead**: ~1.5 KB
- **Total Overhead**: 451.5 KB

3. **Total Memory per Asset**: ~27.1 MB

**Scaling this to 30 assets**
- **Total Texture Memory**: ~799.5 MB
- **Total Material Overhead**: ~13.5 MB
- **Total Memory Impact**: ~813 MB

## Addtional Considerations

1. **Texture Streaming**: Unreal Engine uses texture streaming to manage VRAM usage, so naturally not all textures may be loaded at full resolution at the same time, at a given point in time.

2. **Shared Materials**: If assets share the same materal but with different parameter values, we would only count the overhead of the base material once

3. **Texture Sampling**: Actual performance impact also depends on how the textures are sampled in the shader.

# Master Material with Instanced Materials from it

- 30 assets
- Avg. 5 materials per asset (150 total material instances)
- Each material is 5 textures @ 2K
- All instances derive from a single Master material

#### Memory Components

1. **Master Material Overhead**
2. **Material Instance Overhead**
3. **Texture Memory**

## 1. Master Material Ovehead

Typically the Master material is compiled once and it includes:

- **Base material data**: ~150 KB
- **Shader variants (assume medium complexity with 4 variants)**: ~300 KB (4 x 75 KB)
- **Total Master Material Overhead**: ~450 LB

## 2. Material Instance Overhead

Each material instance has minimal overhead:

- **Instance parameter data**: ~1.5 KB per instance
- **150 instances (30 assets x 5 materials)**: 150 x 1.5 = 225 KB
- **Total Instance Overhead**: ~225 KB

## 3. Texture Memory

For 2K textures with different compression formats:

- **Color (RGB)**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **ORM**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **Normal**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT7)
- **Emissive**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)
- **Mask**: 2048 x 2048 x 1 x 1.33 = 5.33 MB (DXT5)

- **Total per material set**: ~26.65 MB

For 150 material instances (assuming unique textures):

150 x 26.65 MB = 3,997.5 MB

- **Total Texture Memory**: ~3,997.5 MB (~3.9 GB)

**Using a Mater Material approach with instances is extremely memory efficient from a shader perspective.**

**The vast majority of memory usage (~99.98%) comes from textures themselves, not the materal overhead.**

---

# Compiled Shader Variants

## **What Are Shader Variants?**

Shader variants are different compiled versions of the same base material shader that are optimised for specific rendering scenarios or platforms. Each variant is a separate compiled shader program that gets stored in memory.
The 4 Common Shader Variants in Medium Complexity Materials

For a medium complexity material in Unreal Engine, these typically include:

- **Base Variant**: The standard shader used for normal rendering in the main view.

- **Mobile Variant**: A simplified version optimised for mobile platforms with reduced features and complexity.

- **High-Quality Variant**: An enhanced version with additional features enabled for close-up or high-detail scenarios.

- **Distance Field Variant**: A specialized version used for distance field effects like ambient occlusion, shadows, or global illumination.

#### **Additional Possible Variants**

Depending on the project settings and material complexity, there might be additional variants:

- **Different LOD Variants**: Simplified versions for distant objects
- **Virtual Texturing Variant**: For materials using virtual texturing
- **Ray Tracing Variant**: For ray tracing-compatible materials
- **Platform-Specific Variants**: Different versions for DirectX, Vulkan, Metal, etc.

#### **Memory Impact**

Each variant requires separate compilation and storage in memory. The ~75 KB per variant is an approximation of the compiled shader code size for a medium-complexity material. More complex materials with many nodes and operations will have larger compiled shader sizes.