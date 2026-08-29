from app.services.knowledge_base import seed_handbook


def main() -> None:
    added, removed = seed_handbook()
    print(f"公司手册索引已更新：写入 {added} 个分块，移除 {removed} 个旧分块。")


if __name__ == "__main__":
    main()
