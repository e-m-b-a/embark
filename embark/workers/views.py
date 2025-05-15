from django.http import JsonResponse


def connect_worker(request, worker_id):
    return JsonResponse({'worker_id': worker_id})