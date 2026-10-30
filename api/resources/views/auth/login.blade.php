@extends('layouts.app', ['title' => 'Log in'])

@section('content')
    <div class="mx-auto mt-10 max-w-sm">
        <h1 class="text-xl font-semibold">Log in</h1>
        <p class="mt-1 text-sm text-slate-500">Demo account: <code class="rounded bg-slate-100 px-1">{{ $demoEmail }}</code>
            (password in your <code>.env</code>, <code>DEMO_USER_PASSWORD</code>).</p>
        <form method="POST" action="{{ url('login') }}" class="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-5">
            @csrf
            <label class="block text-sm">
                <span class="text-slate-600">Email</span>
                <input name="email" type="email" value="{{ old('email', $demoEmail) }}" required autofocus
                       class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none">
            </label>
            <label class="block text-sm">
                <span class="text-slate-600">Password</span>
                <input name="password" type="password" required
                       class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none">
            </label>
            <button class="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">Log in</button>
        </form>
    </div>
@endsection
