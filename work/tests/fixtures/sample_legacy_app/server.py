"""Legacy service entry point with an unavailable development dependency."""

import sample_external_database_driver

from legacy_shop import checkout_total


def main() -> None:
    database = sample_external_database_driver.connect()
    database.serve(checkout_total)


if __name__ == "__main__":
    main()
