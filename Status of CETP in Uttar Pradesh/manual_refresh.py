from scrap import (
    scrape_and_create_json,
    backup_current_to_audit,
    clear_current,
    save_to_mysql
)

def main():

    print("=" * 80)
    print("MANUAL REFRESH STARTED")
    print("=" * 80)

    scrape_and_create_json()

    backup_current_to_audit()

    clear_current()

    save_to_mysql()

    print("=" * 80)
    print("MANUAL REFRESH COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()