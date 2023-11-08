// include https://code.jquery.com/jquery-3.6.0.min.js



$(document).ready(function() {
    //declare the presignedUrlvariable
    let presignedUrl;
    let api_backend_url = "https://grl6bha8b4.execute-api.us-east-1.amazonaws.com/prod/";
    let cognito_url = "https://idp-br-domain-demo.auth.us-east-1.amazoncognito.com/login?client_id=55u724thniatbr27vhilrj0qtl&response_type=token&redirect_uri=https://d2fl4tlxj4g8l.cloudfront.net/index.html";
    const loadingOverlay = $("#loading-overlay");
    
    const loginButton = $("#login-button");
    const loginContainer = $("#login-container");
    const documentSelection = $("#document-selection");
    const openDocumentButton = $("#open-document-button");
    const searchContainer = $("#search-container");
    const documentDropdown = $("#document-dropdown");
    const searchButton = $("#search-button");
    const searchInput = $("#search-input");
    const searchResultsContainer = $("#search-results-container");
    const imageUploadContainer = $("#image-upload-container");
    const submitButton = $("#submit-button");
    imageUploadContainer.hide();
    searchResultsContainer.hide();
    // Display search results
    function displaySearchResults(results) {
        
        searchResultsContainer.show();
        searchResultsContainer.empty();
        
        if (results && results.length > 0) {
            const ul = $("<ul>");
            results.forEach(result => {
                const li = $("<li>").text(result);
                ul.append(li);
            });
            searchResultsContainer.append(ul);
        } else {
            searchResultsContainer.text('No results found.');
        }
    }
    
    
    // Fetch list of documents from API
    function fetchDocuments(session) {
        // ... (same code as in the previous response)
        
        fetch(apiUrl, requestData)
            .then(response => response.json())
            .then(data => {
                // Populate document selection dropdown
                populateDocumentDropdown(data.documents);
                
                // Show document selection UI
                documentSelection.show();
            })
            .catch(error => {
                console.error('Error fetching documents', error);
            });
    }
    
    // Populate document selection dropdown
    function populateDocumentDropdown(documents) {
        documentDropdown.empty();
        
        if (documents && documents.length > 0) {
            documents.forEach(document => {
                const option = $("<option>")
                    .attr("value", document.s3Key)
                    .text(document.name);
                documentDropdown.append(option);
            });
        } else {
            const option = $("<option>").text("No documents available");
            documentDropdown.append(option);
        }
    }
    // Open selected document
    openDocumentButton.click(function() {
        
        searchResultsContainer.empty();
        searchResultsContainer.hide();
        searchContainer.show();
    });

    // Search functionality
    searchButton.click(function() {
        showLoadingOverlay();
        loadCredentials().then(id_token => {
            const searchText = searchInput.val();
            headers = {
                'Authorization': 'Bearer ' + id_token
            }
            post(api_backend_url+"api_backend", {
                'query': searchText,
                // get the selected document from the dropdown menu
                'key': documentDropdown.val(),
    
            },headers).then(response => {
                // show the response in the in the search results container
                hideLoadingOverlay();
                searchResultsContainer.empty();
                searchResultsContainer.show();
                searchResultsContainer.text(response);
            });
        });
        
    });
    // Function to show the loading overlay
    function showLoadingOverlay() {
        loadingOverlay.show();
    }

    // Function to hide the loading overlay
    function hideLoadingOverlay() {
        loadingOverlay.hide();
    }
    // a function that takes an s3 signed url as a parameter and uses it to upload a file. 
    function uploadFile(signedUrl="https://some.s3.amazonaws.com/") {
        // get the file from the input
        const file = $("#image-upload")[0].files[0];
        // make a request to the signed url
        $.ajax({
            contentType: 'binary/octet-stream',
            url: signedUrl,
            type: 'PUT',
            data: file,
            processData: false
        });
    }
    hideLoadingOverlay();
    // Call the showLoadingOverlay function when you want to display the overlay
    // Call the hideLoadingOverlay function when your
    
    // a fucntion that does a jquery post
    function post(url, data, headers={}) {
        return $.ajax({
            type: 'POST',
            url: url,
            data: JSON.stringify(data),
            dataType: 'json',
            headers: headers
            }
        );
    }
    // a fucntion tha does a jquery get.
    function get(url, headers={}) {
        return $.ajax({
            type: 'GET',
            url: url,
            headers: headers
        });
    }
    // a function that uses get to get the presigned url from this api_backend_url and receives the id_token
    function get_presigned_url(id_token) {
        // create a header Authorization with the id_token
        headers = {
            'Authorization': 'Bearer ' + id_token
        }
        // do a get request to this endpoint /get_presigned_url
        return get(api_backend_url+'api_backend', headers).then(response => {
            // and return the presigned url
            return response;
        });
    }
    // a function that loads cognito credentials for an api request
    function loadCredentials() {
        return new Promise((resolve, reject) => {
            // get the id_token from the query string
            const id_token = window.location.hash.match(/id_token=([^&]+)/);
            // check if id_token has [1] index
            // check if id_token is not null
            // check if id_token is not undefined
            if (id_token === null || typeof id_token[1] === 'undefined')   {
                //reject(cognito_url);
                resolve("temptoken");
            }
            // otherwise, resolve with the id_token
            resolve(id_token[1]);
        });
    }
    function get_user_files(id_token) {
        // create a header Authorization with the id_token
        headers = {
            'Authorization': 'Bearer ' + id_token
        }
        // do a get request to this endpoint /get_user_files
        return post(api_backend_url+"get_user_files",{}, headers).then(response => {
            // and return the presigned url
            return response;
        });
    }
    // if id_token is present in the query string
    if (window.location.hash.includes('id_token')) {
        // get a pressigned url from the api
        showLoadingOverlay();
        loginContainer.hide();
        imageUploadContainer.show();
        loadCredentials().then(id_token => {
            
            get_user_files(id_token).then(response => {
                // and get the list of files from the response
                const files = response;
                // populate the dropdown with the list of files
                populateDocumentDropdown(files);
                // show the document selection UI
                hideLoadingOverlay();
                documentSelection.show();
            });
        });
        
        submitButton.click(function() {
            showLoadingOverlay();
            loadCredentials().then(id_token => {
                get_presigned_url(id_token).then(response => {
                    // store the presigned url in a global mutable variable
                    presignedUrl = response;
                    uploadFile(presignedUrl['presigned_url']);
                    hideLoadingOverlay();
                });
                
            });
        });
    }else {
        window.location.href = cognito_url;
    }
    

});