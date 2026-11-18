from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class AccountsTests(APITestCase):
    def setUp(self):
        self.html_signup_url = reverse('accounts:signup')
        self.html_login_url = reverse('accounts:login')
        self.api_signup_url = reverse('accounts:api-signup')
        self.api_login_url = reverse('accounts:api-login')
        self.api_logout_url = reverse('accounts:api-logout')

        self.user = User.objects.create_user(
            username='existing_user',
            email='test@example.com',
            password='StrongPassword123!',
        )

    def test_html_signup_logs_user_in_and_redirects_to_tracker(self):
        """HTML-регистрация сразу логинит пользователя в сессию и ведет в трекер"""
        resp = self.client.post(self.html_signup_url, data={
            'username': 'html_user',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('tracker:medicine_list'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_api_signup_success_and_validation(self):
        """POST /accounts/api/signup/ создает юзера (201) или возвращает 400 при слабом пароле"""
        bad_resp = self.client.post(
            self.api_signup_url,
            data={'username': 'weak_user', 'password': '123'},
            format='json',
        )
        self.assertEqual(bad_resp.status_code, status.HTTP_400_BAD_REQUEST)

        good_resp = self.client.post(
            self.api_signup_url,
            data={'username': 'api_user', 'email': 'api@example.com', 'password': 'StrongPassword123!'},
            format='json',
        )
        self.assertEqual(good_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(good_resp.data['username'], 'api_user')
        self.assertIn('_auth_user_id', self.client.session)

    def test_api_login_and_logout(self):
        """POST /accounts/api/login/ (200/400) и POST /accounts/api/logout/ (204)"""
        bad_login = self.client.post(
            self.api_login_url,
            data={'username': 'existing_user', 'password': 'WrongPassword'},
            format='json',
        )
        self.assertEqual(bad_login.status_code, status.HTTP_400_BAD_REQUEST)

        good_login = self.client.post(
            self.api_login_url,
            data={'username': 'existing_user', 'password': 'StrongPassword123!'},
            format='json',
        )
        self.assertEqual(good_login.status_code, status.HTTP_200_OK)
        self.assertIn('_auth_user_id', self.client.session)

        logout_resp = self.client.post(self.api_logout_url)
        self.assertEqual(logout_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn('_auth_user_id', self.client.session)