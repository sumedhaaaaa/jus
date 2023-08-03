from django.shortcuts import render,redirect
from django.http import JsonResponse, response
import json
import razorpay
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from .forms import CreateUserForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

@csrf_exempt
def registerPage(request):
	if request.user.is_authenticated:
		return redirect('store')
	else:
		form = CreateUserForm()
		if request.method == 'POST':
			form = CreateUserForm(request.POST)
			if form.is_valid():
				user=form.save()
				Customer.objects.create(
					user=user,
					name=user.username,
					email=user.email,
				)
				username= form.cleaned_data.get('username')    
				messages.success(request, 'User ' + username + ' Registered')

				return redirect('login')
			

		context = {'form':form}
		return render(request, 'store/register.html', context)



@csrf_exempt
def loginPage(request):
	if request.user.is_authenticated:
		return redirect('home')
	else:
		if request.method == 'POST':
			username = request.POST.get('username')
			password =request.POST.get('password')

			user = authenticate(request, username=username, password=password)

			if user is not None:
				login(request, user)
				return redirect('store')
			else:
				messages.info(request, 'Username OR Password is incorrect')

		context = {}
		return render(request, 'store/login.html', context)

def logoutUser(request):
	logout(request)
	return redirect('store')

def store(request):
	data = cartData(request)

	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	products = Product.objects.all()
	context = {'products':products, 'cartItems':cartItems}
	return render(request, 'store/store.html', context)


def cart(request):
	data = cartData(request)

	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/cart.html', context)

def checkout(request):

	client = razorpay.Client(auth=("rzp_test_EA6IA1F18zib3c", "jcbdcts7WyGH2LEZQkzlS6kA"))
	order_amount = 50000
	order_currency = 'INR'
	order_receipt = 'order_rcptid_11'
	notes = {'Shipping address': 'Bommanahalli, Bangalore'}   # OPTIONAL

	payment = client.order.create({'amount': order_amount, 'currency' : order_currency,})

	
	data = cartData(request)
	
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems,}
	return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

@csrf_exempt
def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)

	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, data)

	total = float(data['form']['total'])
	razorpay_id=str(data['transaction_id'])
	if razorpay_id=="":
		order.transaction_id = transaction_id
	else:
		order.transaction_id = razorpay_id

	if total == order.get_cart_total:
		order.complete = True
		order.amount=order.get_cart_total
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
		customer=customer,
		order=order,
		roomno=data['shipping']['roomno'],
		floor=data['shipping']['floor'],
		hostel=data['shipping']['hostel'],
		block=data['shipping']['block'],
		)

	return JsonResponse('Payment submitted..', safe=False)
