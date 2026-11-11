from src.application.enums import SubjectType
from src.product.enums import FILE_FIELD_TYPES, LANGUAGES
from src.product.seed import CATEGORIES, _product


def test_seed_products_are_valid():
    assert [len(products) for _, products in CATEGORIES] == [7, 6]
    for data in (data for _, products in CATEGORIES for data in products):
        product = _product(data, category_id=1)
        assert [t.language for t in product.translations] == list(LANGUAGES)
        assert all(t.description for t in product.translations)
        assert set(product.allowed_subject_types) <= {s.value for s in SubjectType}
        numbers = [stage.number for stage in product.stages]
        assert numbers == list(range(1, len(numbers) + 1))
        for stage in product.stages:
            assert stage.fields and len(stage.translations) == 3
            for field in stage.fields:
                assert [t.language for t in field.translations] == list(LANGUAGES)
                assert all(2 <= len(t.name) <= 255 for t in field.translations)
                if field.field_type not in FILE_FIELD_TYPES:
                    assert field.max_files == 1
        assert product.stages[0].fields[0].field_type == "NUMBER"
