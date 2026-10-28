from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import resolve_url
from django.template import RequestContext, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from recipe.models import Recipe
from .services import cast_vote, toggle_bookmark

User = get_user_model()


class RecipeActionsTagTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="tag-author")
        self.viewer = User.objects.create_user(username="tag-viewer")
        self.recipe = Recipe.objects.create(title="Tumis Kangkung", author=author)
        cast_vote(self.viewer, self.recipe, 1)

    def render_for(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return Template(
            "{% load voting_tags %}{% recipe_actions recipe %}"
        ).render(RequestContext(request, {"recipe": self.recipe}))

    def test_anonymous_sees_score_and_login_link_but_no_buttons(self):
        html = self.render_for(AnonymousUser())
        self.assertIn(">1</span>", html)
        self.assertIn("Masuk untuk vote", html)
        self.assertIn(resolve_url(settings.LOGIN_URL), html)
        self.assertNotIn("vote__btn", html)
        self.assertNotIn('class="bookmark', html)
        self.assertNotIn("upvote,", html)

    def test_breakdown_is_only_for_signed_in_users(self):
        html = self.render_for(self.viewer)
        self.assertIn("1 upvote, 0 downvote", html)
        self.assertIn("vote__btn", html)

    def test_signed_in_state_is_rendered(self):
        toggle_bookmark(self.viewer, self.recipe)
        html = self.render_for(self.viewer)
        self.assertIn("is-up", html)
        self.assertIn("is-saved", html)
        self.assertIn(reverse("voting:vote", args=[self.recipe.pk]), html)