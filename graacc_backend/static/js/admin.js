async function adminLogin(email, senha, csrftoken) {
    const response = await fetch("/graacc/api/admin/login", 
    {
        method: "POST",
        headers: {
            'X-CSRFToken': csrftoken,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email, senha
        })
    });

    return await response.json();
}