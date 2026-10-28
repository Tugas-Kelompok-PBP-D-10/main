from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
import uuid

from .models import Inventori, Bahan

# Create your tests here.

class InventoriTest(TestCase):
    def setUp(self):
        # Buat dua objek User
        self.user1 = User.objects.create_user("andi", "andi@example.com", "sayaAndi123")
        self.user2 = User.objects.create_user("budi", "budi@example.com", "sayaBudi321")
        
        # Cari inventori
        self.inventori1 = Inventori.objects.get(user=self.user1)
        self.inventori2 = Inventori.objects.get(user=self.user2)
        # Buat 2 bahan
        self.bahan1 = Bahan.objects.create(name="Ayam", stock=3, inventory=self.inventori1)
        self.bahan2 = Bahan.objects.create(name="Nasi", stock=5, inventory=self.inventori2)

        self.client.force_login(self.user1)


    # Test halaman Inventori
    def test_inventori_url_is_accessible(self):
        response = self.client.get(reverse("inventori"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventori.html")
        self.assertContains(response, f'href="{reverse("update_inventori")}"')

    def test_nonexistent_page_returns_404(self):
        response = self.client.get("/halaman-yang-tidak-ada/")

        self.assertEqual(response.status_code, 404)

    # Test model Inventori
    def test_inventori_model(self):
        self.assertEqual(self.inventori1.user, self.user1)
        self.assertEqual(self.inventori2.user, self.user2)

    # Test model Bahan
    def test_bahan_model(self):
        self.assertEqual(self.bahan1.name, "Ayam")
        self.assertEqual(self.bahan1.stock, 3)
        self.assertEqual(self.bahan1.inventory, self.inventori1)

    # Test get_bahan_json
    def test_get_bahan_json(self):
        response = self.client.get(reverse("get_bahan_json"))
        self.assertContains(response, "Ayam")
        self.assertNotContains(response, "Nasi")

    def test_empty_get_bahan_json(self):
        Bahan.objects.all().delete()
        response = self.client.get(reverse("get_bahan_json"))
        self.assertEqual(response.json(), [])

    # Test update_inventori
    def test_get_update_inventori_page(self):
        response = self.client.get(reverse('update_inventori'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "components/update_inventori.html")
        self.assertIn("formset", response.context)

    def test_post_valid_formset_updates_data(self):
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-id': self.bahan1.id,
            'form-0-name': 'Sayur',
            'form-0-stock': 15, 
        }
        
        response = self.client.post(reverse('update_inventori'), data)
        
        self.assertRedirects(response, reverse("inventori"))
        
        self.bahan1.refresh_from_db()
        self.assertEqual(self.bahan1.stock, 15)
        self.assertEqual(self.bahan1.name, 'Sayur')

    def test_post_invalid_formset_shows_error(self):
        data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-0-id': self.bahan1.id,
            'form-0-name': 'Tepung',
            'form-0-stock': 0, 
        }
        
        response = self.client.post(reverse('update_inventori'), data)
        
        messages = list(get_messages(response.wsgi_request))
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Gagal menyimpan: Pastikan stok tidak 0")
        self.assertEqual(response.status_code, 200)

    # Test delete_bahan
    def test_post_deletes_item_and_redirects(self):
        response = self.client.post(reverse('delete_bahan', args=[self.bahan2.id]))
        
        self.assertRedirects(response, reverse("update_inventori"))
        
        self.assertFalse(Bahan.objects.filter(id=self.bahan2.id).exists())
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Bahan berhasil dihapus!")

    def test_get_does_not_delete_item(self):
        response = self.client.get(reverse('delete_bahan', args=[self.bahan2.id]))
        
        self.assertRedirects(response, reverse("update_inventori"))
        
        self.assertTrue(Bahan.objects.filter(id=self.bahan2.id).exists())

    def test_nonexistent_item_returns_404(self):
        invalid_url = reverse('delete_bahan', args=[uuid.uuid4()]) 
        
        response = self.client.post(invalid_url)
        
        self.assertEqual(response.status_code, 404)

    # Test add_bahan
    def test_post_valid_data_creates_bahan(self):
        data = {
            "name": "Kacang",
            "stock": 20,
            "inventori": self.inventori1,
        }

        response = self.client.post(reverse('add_bahan'), data)

        self.assertEqual(response.status_code, 201)
        
        json_data = response.json()
        self.assertIn("message", json_data)
        self.assertEqual(json_data["message"], "Bahan berhasil ditambahkan.")
        self.assertIn("pk", json_data)

        bahan = Bahan.objects.get(id=json_data["pk"])
        self.assertEqual(bahan.name, "Kacang")
        self.assertEqual(bahan.stock, 20)
        self.assertEqual(bahan.inventory, self.inventori1)

    def test_post_invalid_data_returns_400_with_errors(self):
        data = {
            "name": "",  # Empty required field
            "stock": -5, # Assuming negative stock is invalid in your model/form
        }

        response = self.client.post(reverse('add_bahan'), data)

        self.assertEqual(response.status_code, 400)
        
        json_data = response.json()
        self.assertIn("errors", json_data)
        
        self.assertIn("name", json_data["errors"])
        self.assertIn("stock", json_data["errors"])

    def test_post_stock_zero_returns_400(self):
        data = {
            "name": "Roti", 
            "stock": 0, 
        }
    
        response = self.client.post(reverse('add_bahan'), data)
    
        self.assertEqual(response.status_code, 400)
    