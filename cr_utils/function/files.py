import os
import base64, json
import zstandard as zstd
from tqdm import tqdm


def read_jsonl(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]


def write_jsonl(data: dict, file_path: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def compress_files(source_dir, output_file="compressed.txt", filter_func=None, compression_level=3):
    """
    使用 Zstandard 压缩指定目录下所有满足 filter_func 条件的文件到单个纯文本文件，保留目录结构，并显示进度条。

    Args:
        source_dir (str): 包含文件的源目录。
        output_file (str): 压缩后输出的纯文本文件路径。
        filter_func (callable, optional): 一个函数，接受文件完整路径作为参数，
                                         如果返回 True 则处理该文件，否则忽略。
                                         默认为 None，表示处理所有文件。
        compression_level (int): Zstandard 压缩级别，范围通常是 1-22。
                                 更高的级别意味着更高的压缩比和更长的压缩时间。
    """
    compressed_blocks = []

    files_to_process = []
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if filter_func is None or filter_func(file_path):
                files_to_process.append(file_path)

    # 创建 Zstandard 压缩器
    cctx = zstd.ZstdCompressor(level=compression_level)

    print(f"开始使用 Zstandard (级别: {compression_level}) 压缩 {len(files_to_process)} 个文件到 {output_file}...")
    for file_path in tqdm(files_to_process, desc="压缩文件"):
        try:
            relative_path = os.path.relpath(file_path, source_dir)
            encoded_relative_path = base64.b64encode(relative_path.encode('utf-8')).decode('utf-8')

            with open(file_path, 'rb') as f:
                file_content_bytes = f.read()

            # 使用 Zstandard 压缩
            compressed_content_bytes = cctx.compress(file_content_bytes)
            encoded_compressed_content = base64.b64encode(compressed_content_bytes).decode('utf-8')

            separator = "---FILE_SEPARATOR---"
            compressed_blocks.append(f"{encoded_relative_path}{separator}{encoded_compressed_content}")
        except Exception as e:
            print(f"\n警告：处理文件失败：{file_path}，错误：{e}")
            continue

    with open(output_file, 'w', encoding='utf-8') as out_f:
        out_f.write("\n".join(compressed_blocks))

    print(f"\n所有满足条件的文件已成功压缩并保存到：{output_file}")


def decompress_files(compressed_file, output_dir="decompressed"):
    """
    使用 Zstandard 解析压缩后的纯文本文件，并还原文件到指定的输出目录，显示进度条。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(compressed_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    separator = "---FILE_SEPARATOR---"
    dctx = zstd.ZstdDecompressor() # 创建 Zstandard 解压器

    print(f"开始使用 Zstandard 解压 {len(lines)} 个文件到 {output_dir}...")
    for line in tqdm(lines, desc="解压文件"):
        line = line.strip()
        if not line:
            continue

        try:
            parts = line.split(separator, 1)
            if len(parts) != 2:
                print(f"\n警告：跳过格式不正确的行：{line[:50]}...")
                continue

            encoded_relative_path, encoded_compressed_content = parts

            relative_path_bytes = base64.b64decode(encoded_relative_path)
            relative_path = relative_path_bytes.decode('utf-8')

            compressed_content_bytes = base64.b64decode(encoded_compressed_content)
            # 使用 Zstandard 解压
            decompressed_content_bytes = dctx.decompress(compressed_content_bytes)

            output_file_path = os.path.join(output_dir, relative_path)
            output_file_dir = os.path.dirname(output_file_path)

            if not os.path.exists(output_file_dir):
                os.makedirs(output_file_dir)

            with open(output_file_path, 'wb') as out_f:
                out_f.write(decompressed_content_bytes)

        except Exception as e:
            print(f"\n警告：处理行时发生错误：{line[:50]}... 错误信息：{e}")
            continue

    print(f"\n所有文件已成功解压到：{output_dir}")
