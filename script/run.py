from cr_utils import compress_files, decompress_files


def main():
    def is_not_png(file_path: str):
        return not file_path.endswith('.png')
    compress_files("tmp", "tmp.txt", is_not_png)

    # 解压缩文件示例
    decompress_files("tmp.txt", "decompressed")


if __name__ == "__main__":
    main()
