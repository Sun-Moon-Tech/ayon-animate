from ayon_animate.lib import FLAutoCreator

class ReviewCreator(FLAutoCreator):
    """Creates review instance which might be disabled from publishing."""
    identifier = "review"
    product_base_type = "review"
    product_type = product_base_type
    default_variant = "Main"

    def get_detail_description(self):
        return """Auto creator for review.

        FLA review is created from all published renders.

        Review might be disabled by an artist (instance shouldn't be deleted as
        it will get recreated in next publish either way).
        """
