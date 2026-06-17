*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource
Test Setup    Open Login Page    ${LOGIN_PAGE_URL}
Test Teardown    Close Browser Session

*** Test Cases ***
TC_LOGIN_001 Verify user can login with valid username and password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

TC_LOGIN_002 Verify login fails with incorrect username and correct password
    Verify Login Page Loaded
    Enter User Name Textbox    invalidUser
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_003 Verify login fails with correct username and incorrect password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    WrongPassword123
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_004 Verify login fails when both username and password are blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${EMPTY}
    Enter Password Textbox    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_005 Verify login fails when username is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${EMPTY}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_006 Verify login fails when password is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_007 Verify login page UI loads correctly
    Verify Login Page Loaded
    Element Should Be Visible    ${USER_NAME_TEXTBOX}
    Element Should Be Visible    ${PASSWORD_TEXTBOX}
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_008 Verify password field masks entered characters
    Verify Login Page Loaded
    Enter Password Textbox    ${VALID_PASSWORD}
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password

TC_LOGIN_009 Verify login using Enter key after entering credentials
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

TC_LOGIN_010 Verify login fails when username contains only whitespace
    Verify Login Page Loaded
    Enter User Name Textbox    ${SPACE}${SPACE}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_011 Verify login fails when password contains only whitespace
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${SPACE}${SPACE}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_012 Verify login with leading and trailing spaces in username
    Verify Login Page Loaded
    Enter User Name Textbox    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_013 Verify login fails when username contains special characters
    Verify Login Page Loaded
    Enter User Name Textbox    haklarr@@@
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_014 Verify login fails with extremely long username input
    Verify Login Page Loaded
    Enter User Name Textbox    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_015 Verify login fails with extremely long password input
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_016 Verify login fails when both username and password are incorrect
    Verify Login Page Loaded
    Enter User Name Textbox    wrongUser
    Enter Password Textbox    wrongPassword
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}

TC_LOGIN_017 Verify repeated clicking of login button does not create multiple requests
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

TC_LOGIN_018 Verify login with copy-paste credentials
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${SIGN_IN_BUTTON}    10s

TC_LOGIN_019 Verify username field retains focus on page load
    Verify Login Page Loaded
    Element Should Be Focused    ${USER_NAME_TEXTBOX}

TC_LOGIN_020 Verify login fails when username case is different
    Verify Login Page Loaded
    Enter User Name Textbox    HAKLARR
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Element Should Be Visible    ${SIGN_IN_BUTTON}
