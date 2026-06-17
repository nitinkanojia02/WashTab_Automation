*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${BROWSER}    chrome
${DEFAULT_TIMEOUT}    10s

*** Keywords ***
Open Browser Session
    [Documentation]    Opens a browser session on a blank page and maximizes the window.
    [Arguments]    ${browser}=${BROWSER}
    Open Browser    about:blank    ${browser}
    Maximize Browser Window

Close Browser Session
    [Documentation]    Closes all open browser instances for the current execution.
    Close All Browsers

Open Browser To Url
    [Documentation]    Opens a browser session and navigates to the provided URL.
    [Arguments]    ${url}    ${browser}=${BROWSER}
    Open Browser Session    ${browser}
    Go To Url    ${url}

Go To Url
    [Documentation]    Navigates the current browser session to the provided URL.
    [Arguments]    ${url}
    Go To    ${url}

Open Login Page
    [Documentation]    Opens the login page in a new browser session using the provided URL.
    [Arguments]    ${url}    ${browser}=${BROWSER}
    Open Browser To Url    ${url}    ${browser}

Wait For Element To Be Ready
    [Documentation]    Waits until the provided locator is visible and enabled.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${locator}    ${timeout}
    Wait Until Element Is Enabled    ${locator}    ${timeout}

Click When Ready
    [Documentation]    Waits for an element and then clicks it.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element To Be Ready    ${locator}    ${timeout}
    Click Element    ${locator}

Input Text When Ready
    [Documentation]    Waits for an element and then inputs the provided text.
    [Arguments]    ${locator}    ${text}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait For Element To Be Ready    ${locator}    ${timeout}
    Input Text    ${locator}    ${text}
