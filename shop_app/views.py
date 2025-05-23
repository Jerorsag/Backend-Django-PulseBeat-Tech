from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Cart, CartItem, Transaction
from .serializers import ProductSerializer, DetailedProductSerializer, CartItemSerializer, SimpleCartSerializer, \
    CartSerializer, UserSerializer
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from decimal import Decimal
import uuid
import requests
import paypalrestsdk
from django.conf import settings
from core.models import CustomUser

BASE_URL = settings.REACT_BASE_URL

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@api_view(["GET"])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def product_detail(request, slug):
    product = Product.objects.get(slug = slug)
    serializer = DetailedProductSerializer(product)
    return Response(serializer.data)

@api_view(["POST"])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")

        cart, created = Cart.objects.get_or_create(cart_code = cart_code)
        product = Product.objects.get(id = product_id)

        cartitem, created = CartItem.objects.get_or_create(cart = cart, product = product)
        cartitem.quantity = 1
        cartitem.save()

        serializer = CartItemSerializer(cartitem)
        return Response({"datat": serializer.data, "message": "Cart Item created successfully"}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["GET"])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    cart = Cart.objects.get(cart_code = cart_code)
    product = Product.objects.get(id = product_id)

    product_exists_in_cart = CartItem.objects.filter(cart = cart, product = product).exists()

    return Response({"product_in_cart": product_exists_in_cart})

@api_view(["GET"])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code = cart_code, paid = False)
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(["GET"])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code = cart_code, paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(["PATCH"])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id = cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({"data": serializer.data, "message": "Cart Item updated successfully!"}, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["POST"])
def delete_cartitem(request):
    cartitem_id = request.data.get("item_id")
    cartitem = CartItem.objects.get(id = cartitem_id)
    cartitem.delete()
    return Response({"message": "Cart Item deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username": user.username})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    if request.user:
        try:
            # Generate a unique transaction reference
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code = cart_code)
            user = request.user

            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4.00")
            total_amount = amount + tax
            currency = "NGN"
            redirect_url = f"{BASE_URL}/payment-status/"

            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=user,
                status='pending'
            )

            flutterwave_payload = {
                "tx_ref": tx_ref,
                "amount": str(total_amount),
                "currency": currency,
                "redirect_url": redirect_url,
                "customer" : {
                    "email": user.email,
                    "username": user.username,
                    "phonenumber": user.phone
                },
                "customizations": {
                    "title": "PulseBeat Tech Payment"
                }
            }

            # Set up the headers for the request
            headers = {
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            # Make the API request to FLUTTERWAVE
            response = requests.post(
                'https://api.flutterwave.com/v3/payments',
                json=flutterwave_payload,
                headers=headers
            )

            # Check if the request was successful
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(response.json(), status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def payment_callback(request):
    status = request.GET.get("status")
    tx_ref = request.GET.get("tx_ref")
    transaction_id = request.GET.get("transaction_id")

    user = request.user

    if status == "successful":
        # Verify the transaction using Flutterwave's API
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }

        response = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify", headers=headers)
        response_data = response.json()

        if response_data["status"] == "success":
            transaction = Transaction.objects.get(ref=tx_ref)

            # Confirm the transaction details
            if(response_data['data']['status'] == "successful"
                    and float(response_data['data']['amount']) == float(transaction.amount)
                    and response_data['data']['currency'] == transaction.currency):
                # Update transaction and cart status to paid
                transaction.status = "completed"
                transaction.save()

                cart = transaction.cart
                cart.paid = True
                cart.user = user
                cart.save()

                return Response({'message': 'Payment succesful!', 'subMessage': 'You have succesfully made payment for items you purchased!'})
            else:
                # Payment verification failed
                return Response({'message': 'Payment verification failed.', 'subMessage': 'Your payment verification failed.'})
        else:
            return Response({'message': 'Failed to verify transaction with Flutterwave.', 'subMessage': 'We could not verify transaction with Flutterwave.'})
    else:
        # Payment was not successful
        return Response({'message': 'Payment was not succesful.'}, status=400)

@api_view(["POST"])
def initiate_paypal_payment(request):
    if request.method == "POST" and request.user.is_authenticated:
        tx_ref = str(uuid.uuid4())
        user = request.user
        cart_code = request.data.get('cart_code')
        cart = Cart.objects.get(cart_code=cart_code)
        amount = sum(item.product.price * item.quantity for item in cart.items.all())
        tax = Decimal("4.00")
        total_amount = amount + tax

        # Create a PayPal payment object
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{BASE_URL}/payment-status?paymentStatus=success&ref={tx_ref}",
                "cancel_url": f"{BASE_URL}/payment-status?paymentStatus=cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "Cart Items",
                        "sku": "cart",
                        "price": str(total_amount),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(total_amount),
                    "currency": "USD"
                },
                "description": "Payment for cart items."
            }]
        })

        print("pay_id", payment)

        transaction, created = Transaction.objects.get_or_create(
            ref=tx_ref,
            cart=cart,
            amount=total_amount,
            user=user,
            status="pending"
        )

        if payment.create():
            for link in payment.links:
                if link in payment.links:
                    if link.rel == 'approval_url':
                        approval_url = str(link.href)
                        return Response({"approval_url": approval_url})
        else:
            return Response({'error': payment.error}, status=400)


@api_view(["GET"])  # Cambiado a GET
def paypal_payment_callback(request):
    try:
        payment_id = request.GET.get('paymentId')  # Cambiado a request.GET
        payer_id = request.GET.get('PayerID')  # Cambiado a request.GET
        ref = request.GET.get('ref')  # Cambiado a request.GET

        print(f"Callback recibido - payment_id: {payment_id}, payer_id: {payer_id}, ref: {ref}")

        if not payment_id or not payer_id or not ref:
            return Response({'error': 'Missing required parameters'}, status=400)

        # Encontrar la transacción sin depender del usuario autenticado
        transaction = Transaction.objects.get(ref=ref)

        # Obtener el usuario de la transacción, no de la solicitud
        user = transaction.user

        # Verifica el pago con PayPal y ejecuta la transacción
        payment = paypalrestsdk.Payment.find(payment_id)

        # Ejecutar el pago - paso crucial que faltaba
        if payment.execute({"payer_id": payer_id}):
            # Actualizar el estado de la transacción
            transaction.status = "completed"
            transaction.save()

            # Actualizar el carrito
            cart = transaction.cart
            cart.paid = True
            cart.user = user
            cart.save()

            return Response({
                'message': 'Payment successful!',
                'subMessage': 'You have successfully made payment for items you purchased!'
            })
        else:
            return Response({'error': payment.error}, status=400)

    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"Error en paypal_payment_callback: {str(e)}")
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=500)


@api_view(["POST"])
def register_user(request):
    try:
        # Extraer los datos del usuario del request
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        # Verificar si el usuario ya existe
        if CustomUser.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists. Please choose a different one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if CustomUser.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already in use. Please use a different email or login."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el nuevo usuario
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Puedes añadir datos adicionales si son proporcionados
        if request.data.get('phone'):
            user.phone = request.data.get('phone')
        if request.data.get('address'):
            user.address = request.data.get('address')
        if request.data.get('city'):
            user.city = request.data.get('city')
        if request.data.get('state'):
            user.state = request.data.get('state')

        user.save()

        # Devuelve una respuesta exitosa
        return Response(
            {"success": "User registered successfully! Please login with your credentials."},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )